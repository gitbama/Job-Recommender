let allJobs = [];
let isAllJobsDisplayed = false;

function toggleLoading(show) {
    const loading = document.getElementById("loading");
    const modalBackground = document.getElementById("modal-background");
    if (show) {
        loading.style.display = "flex";
        modalBackground.style.display = "block";
    } else {
        loading.style.display = "none";
        modalBackground.style.display = "none";
    }
}

document.getElementById("predict-button").addEventListener("click", () => {
    isAllJobsDisplayed = false;

    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = "";
    document.getElementById("load-more-button").style.display = "none";

    const totalJobs = parseInt(document.getElementById("total-jobs").value) || 100;
    const salaryWeight = parseFloat(document.getElementById("salary-weight").value) || 0.25;
    const entryBarrierWeight = parseFloat(document.getElementById("entry-barrier-weight").value) || 0.25;
    const workloadWeight = parseFloat(document.getElementById("workload-weight").value) || 0.25;
    const satisfactionWeight = parseFloat(document.getElementById("satisfaction-weight").value) || 0.25;

    toggleLoading(true);

    fetch("/get_jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            total_jobs: totalJobs,
            salary_weight: salaryWeight,
            entry_barrier_weight: entryBarrierWeight,
            workload_weight: workloadWeight,
            satisfaction_weight: satisfactionWeight
        })
    })
        .then(response => response.json())
        .then(data => {
            toggleLoading(false);

            if (data.error) {
                alert(data.error);
                return;
            }

            allJobs = data;

            if (allJobs.length < totalJobs) {
                alert('요청된 총 직업 수가 API에서 사용 가능한 직업 수를 초과했습니다.');
            }

            displayJobs(allJobs.slice(0, 10), 1);

            document.getElementById("load-more-button").style.display =
                allJobs.length > 10 ? "block" : "none";
        })
        .catch(error => {
            alert("직업 데이터를 불러오는 데 실패했습니다.");
            console.error("Error fetching jobs:", error);
            toggleLoading(false);
        });
});

function displayJobs(jobs, startRank) {
    const resultsDiv = document.getElementById("results");
    jobs.forEach((job, index) => {
        const jobDiv = document.createElement("div");
        jobDiv.classList.add("job-item");
        jobDiv.innerHTML = `
            <h3>${startRank + index}. ${job.job_name}</h3>
            <button class="details-btn" data-job-code="${job.job_code}">추가 정보 보기</button>
        `;
        resultsDiv.appendChild(jobDiv);
    });

    attachDetailsButtonListeners();
}

document.getElementById("load-more-button").addEventListener("click", () => {
    if (isAllJobsDisplayed) return;

    const currentJobsCount = document.getElementById("results").childElementCount;
    const remainingJobs = allJobs.slice(currentJobsCount);
    displayJobs(remainingJobs, currentJobsCount + 1);
    isAllJobsDisplayed = true;
    document.getElementById("load-more-button").style.display = "none";
});

function attachDetailsButtonListeners() {
    document.querySelectorAll(".details-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const jobCode = btn.getAttribute("data-job-code");
            toggleLoading(true);

            fetch(`/get_job_details/${jobCode}`, { method: "GET" })
                .then(response => response.json())
                .then(details => {
                    toggleLoading(false);
                    document.getElementById("modal-job-name").textContent = details.job_nm || "정보 없음";
                    document.getElementById("modal-description").textContent = `하는일: ${details.work || "정보 없음"}`;
                    document.getElementById("modal-required-skills").textContent = `핵심능력: ${details.ability_name || "정보 없음"}`;
                    document.getElementById("modal-training-programs").textContent = `직업훈련: ${details.training || "정보 없음"}`;
                    document.getElementById("modal-research-opportunities").textContent = `진로탐색활동: ${details.research || "정보 없음"}`;
                    document.getElementById("modal-related-orgs").textContent = `관련기관: ${details.rel_org || "정보 없음"}`;
                    document.getElementById("modal-aptitude").textContent = `적성: ${details.aptitude || "정보 없음"}`;
                    document.getElementById("modal-depart-name").textContent = `관련학과: ${details.depart_name || "정보 없음"}`;
                    document.getElementById("modal").style.display = "block";
                    document.getElementById("loading").style.display = "flex";
                    document.querySelector("#loading .spinner").style.display = "none";
                })
                .catch(error => {
                    console.error("Error fetching job details:", error);
                    toggleLoading(false);
                });
        });
    });
}

document.getElementById("modal-close").addEventListener("click", () => {
    document.getElementById("modal").style.display = "none";
    document.getElementById("loading").style.display = "none";
    document.querySelector("#loading .spinner").style.display = "flex";
});

document.querySelectorAll("input[type='range']").forEach(slider => {
    slider.addEventListener("input", e => {
        const input = document.getElementById(`${e.target.id}-input`);
        input.value = e.target.value;
    });
});

document.querySelectorAll("input[type='number']").forEach(numberInput => {
    numberInput.addEventListener("input", e => {
        if (numberInput.id !== "total-jobs") {
            const value = Math.max(0, Math.min(1, e.target.value));
            const slider = document.getElementById(e.target.id.replace("-input", ""));
            slider.value = value;
            e.target.value = value;
        }
    });
});

document.getElementById("toggle-resources-button").addEventListener("click", () => {
    const resourcesList = document.querySelector("#resources ul");
    const toggleButton = document.getElementById("toggle-resources-button");

    if (resourcesList.style.display === "none" || resourcesList.style.display === "") {
        resourcesList.style.display = "block";
        toggleButton.textContent = "접기";
    } else {
        resourcesList.style.display = "none";
        toggleButton.textContent = "펼치기";
    }
});

window.addEventListener("load", () => {
    document.getElementById("total-jobs").value = 100;
    document.getElementById("salary-weight").value = 0.25;
    document.getElementById("entry-barrier-weight").value = 0.25;
    document.getElementById("workload-weight").value = 0.25;
    document.getElementById("satisfaction-weight").value = 0.25;
    document.getElementById("salary-weight-input").value = 0.25;
    document.getElementById("entry-barrier-weight-input").value = 0.25;
    document.getElementById("workload-weight-input").value = 0.25;
    document.getElementById("satisfaction-weight-input").value = 0.25;
});