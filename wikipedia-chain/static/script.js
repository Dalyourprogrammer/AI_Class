const form = document.getElementById("search-form");
const startInput = document.getElementById("start");
const endInput = document.getElementById("end");
const submitBtn = document.getElementById("submit-btn");
const resultDiv = document.getElementById("result");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const start = startInput.value.trim();
    const end = endInput.value.trim();
    if (!start || !end) return;

    setLoading(true);

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000);

        const resp = await fetch("/api/find-chain", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ start, end }),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);

        const data = await resp.json();

        if (data.status === "found") {
            renderChain(data.chain);
        } else if (data.status === "not_found") {
            resultDiv.innerHTML = `<p class="not-found">${data.message}</p>`;
        } else {
            resultDiv.innerHTML = `<p class="error">${data.message}</p>`;
        }
    } catch (err) {
        if (err.name === "AbortError") {
            resultDiv.innerHTML = '<p class="error">Request timed out.</p>';
        } else {
            resultDiv.innerHTML = `<p class="error">Network error: ${err.message}</p>`;
        }
    } finally {
        setLoading(false);
    }
});

function setLoading(loading) {
    startInput.disabled = loading;
    endInput.disabled = loading;
    submitBtn.disabled = loading;
    if (loading) {
        resultDiv.innerHTML = '<p class="loading">Searching...</p>';
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
