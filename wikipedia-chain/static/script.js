const form = document.getElementById("search-form");
const startInput = document.getElementById("start");
const endInput = document.getElementById("end");
const submitBtn = document.getElementById("submit-btn");
const resultDiv = document.getElementById("result");

let pollTimer = null;

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const start = startInput.value.trim();
    const end = endInput.value.trim();
    if (!start || !end) return;

    setLoading(true, "Starting search...");

    try {
        const resp = await fetch("/api/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ start, end }),
        });
        const data = await resp.json();

        if (data.status === "found") {
            renderChain(data.chain);
            setLoading(false);
        } else if (data.status === "ok" && data.job_id) {
            startPolling(data.job_id);
        } else {
            resultDiv.innerHTML = `<p class="error">${data.message}</p>`;
            setLoading(false);
        }
    } catch (err) {
        resultDiv.innerHTML = `<p class="error">Network error: ${err.message}</p>`;
        setLoading(false);
    }
});

function startPolling(jobId) {
    if (pollTimer) clearInterval(pollTimer);

    pollTimer = setInterval(async () => {
        try {
            const resp = await fetch(`/api/search/${jobId}`);
            const data = await resp.json();

            if (data.status === "searching") {
                resultDiv.innerHTML = `<p class="loading">${data.progress || "Searching..."}</p>`;
            } else if (data.status === "found") {
                stopPolling();
                renderChain(data.chain);
                setLoading(false);
            } else {
                stopPolling();
                const cls = data.status === "not_found" ? "not-found" : "error";
                resultDiv.innerHTML = `<p class="${cls}">${data.message}</p>`;
                setLoading(false);
            }
        } catch (err) {
            stopPolling();
            resultDiv.innerHTML = `<p class="error">Polling error: ${err.message}</p>`;
            setLoading(false);
        }
    }, 1500);
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

function setLoading(loading, message) {
    startInput.disabled = loading;
    endInput.disabled = loading;
    submitBtn.disabled = loading;
    if (loading && message) {
        resultDiv.innerHTML = `<p class="loading">${message}</p>`;
    }
}

function renderChain(chain) {
    const div = document.createElement("div");
    div.className = "chain";
    chain.forEach((article, i) => {
        const a = document.createElement("a");
        a.href = article.url;
        a.textContent = article.title;
        a.target = "_blank";
        a.rel = "noopener";
        div.appendChild(a);
        if (i < chain.length - 1) {
            const arrow = document.createElement("span");
            arrow.className = "arrow";
            arrow.textContent = "\u2192";
            div.appendChild(arrow);
        }
    });
    resultDiv.innerHTML = "";
    resultDiv.appendChild(div);
}
