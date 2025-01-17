from flask import Flask, render_template, request, jsonify
import requests
import numpy as np
import tensorflow as tf
import concurrent.futures
import os

app = Flask(__name__)

API_KEY = os.environ.get('API_KEY')

def get_job_data(api_key, page, per_page):
    url = f"https://www.career.go.kr/cnet/front/openapi/jobs.json?apiKey={api_key}&pageIndex={page}&pageSize={per_page}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = response.json()
            return [{'job_cd': job['job_cd']} for job in data.get('jobs', [])]
        except ValueError:
            pass
    return []

def fetch_job_details(api_key, seq, fields=None):
    url = f"https://www.career.go.kr/cnet/front/openapi/job.json?apiKey={api_key}&seq={seq}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            job_details = response.json()
            if fields:
                return {field: job_details.get(field, {}) for field in fields}
            return job_details
        except ValueError:
            pass
    return {}

def standardize(data):
    mean = np.mean(data)
    std = np.std(data)
    return [(x - mean) / std if std != 0 else x for x in data]

def get_first_item_value(data, key, default='정보 없음'):
    if isinstance(data, list) and len(data) > 0:
        return data[0].get(key, default)
    return default

workload_mapping = {
    "보통미만": 3,
    "보통이상": 5,
    "좋음": 7
}

entry_barrier_mapping = {
    "법률 및 사회활동 관련직": 7,
    "금융 및 경영 관련직": 6,
    "인문계 교육 관련직": 5,
    "기획서비스직": 4,
    "영업관련 서비스직": 3,
    "농생명산업 관련직": 2,
    "기타": 5
}

default_satisfaction = 70

def process_job(job, job_codes, job_names, salaries, entry_barriers, workloads, satisfactions):
    job_code = job['job_cd']
    job_details = fetch_job_details(API_KEY, job_code, ['baseInfo'])
    base_info = job_details.get('baseInfo', {})

    job_codes.append(job_code)
    job_names.append(base_info.get('job_nm', '정보 없음'))

    wage = base_info.get('wage', "4000")
    wage = wage.replace(",", "")
    salary = int(wage) * 10000
    salaries.append(salary)

    workload = workload_mapping.get(base_info.get('wlb'), 5)
    workloads.append(workload)

    aptit_name = base_info.get('aptit_name', '기타')
    entry_barrier = entry_barrier_mapping.get(aptit_name, 5)
    entry_barriers.append(entry_barrier)

    satisfaction = base_info.get('satisfication', default_satisfaction)
    satisfactions.append(float(satisfaction))

@app.route('/get_jobs', methods=['POST'])
def get_jobs():
    try:
        data = request.json
        salary_weight = data.get('salary_weight', 0.25)
        entry_barrier_weight = data.get('entry_barrier_weight', 0.25)
        workload_weight = data.get('workload_weight', 0.25)
        satisfaction_weight = data.get('satisfaction_weight', 0.25)

        total_weight = salary_weight + entry_barrier_weight + workload_weight + satisfaction_weight
        salary_weight /= total_weight
        entry_barrier_weight /= total_weight
        workload_weight /= total_weight
        satisfaction_weight /= total_weight

        total_jobs = max(int(data.get('total_jobs', 100)), 1)

        jobs = []
        page = 1

        while len(jobs) < total_jobs:
            job_data = get_job_data(API_KEY, page, 50)
            if not job_data:
                break
            jobs.extend(job_data)
            page += 1

        jobs = jobs[:total_jobs]
        salaries, entry_barriers, workloads, satisfactions, job_codes, job_names = [], [], [], [], [], []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_job, job, job_codes, job_names, salaries, entry_barriers, workloads, satisfactions) for job in jobs]
            concurrent.futures.wait(futures)

        salaries_standardized = standardize(salaries)
        entry_barriers_standardized = standardize(entry_barriers)
        workloads_standardized = standardize(workloads)
        satisfactions_standardized = standardize(satisfactions)

        x_train = np.array(list(zip(salaries_standardized, entry_barriers_standardized, workloads_standardized, satisfactions_standardized)))
        y_train = np.array([
            (salary_weight * s) + (entry_barrier_weight * eb) + (workload_weight * wl) + (satisfaction_weight * sat)
            for s, eb, wl, sat in zip(salaries_standardized, entry_barriers_standardized, workloads_standardized, satisfactions_standardized)
        ])

        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(4,)),
            tf.keras.layers.Dense(units=1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(x_train, y_train, epochs=100, verbose=0)
        predictions = model.predict(x_train).flatten()
        
        sorted_indices = np.argsort(predictions)[::-1]

        all_jobs = [
            {
                "rank": idx + 1,
                "job_name": job_names[i],
                "job_code": job_codes[i]
            }
            for idx, i in enumerate(sorted_indices)
        ]
        return jsonify(all_jobs)

    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": "직업 데이터를 불러오는 데 실패했습니다.", "details": str(e)}), 500

@app.route('/get_job_details/<job_code>', methods=['GET'])
def get_job_details(job_code):
    try:
        job_details = fetch_job_details(API_KEY, job_code, ['baseInfo', 'workList', 'abilityList', 'jobReadyList', 'researchList', 'jobRelOrgList', 'aptitudeList', 'departList'])
        base_info = job_details.get('baseInfo', {})

        detailed_info = {
            "job_nm": base_info.get('job_nm', '정보 없음'),
            "work": get_first_item_value(job_details.get('workList', []), 'work'),
            "ability_name": get_first_item_value(job_details.get('abilityList', []), 'ability_name'),
            "training": get_first_item_value(job_details.get('jobReadyList', {}).get('training', []), 'training'),
            "research": get_first_item_value(job_details.get('researchList', []), 'research'),
            "rel_org": get_first_item_value(job_details.get('jobRelOrgList', []), 'rel_org'),
            "aptitude": get_first_item_value(job_details.get('aptitudeList', []), 'aptitude'),
            "depart_name": get_first_item_value(job_details.get('departList', []), 'depart_name')
        }
        return jsonify(detailed_info)

    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": "상세 정보를 불러오는 데 실패했습니다.", "details": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)