const form = document.getElementById("ask-form");
const queryInput = document.getElementById("query");
const topKInput = document.getElementById("top-k");
const submitBtn = document.getElementById("submit-btn");
const answerEl = document.getElementById("answer");
const sourcesEl = document.getElementById("sources");
const statusEl = document.getElementById("status");
const sourceCountEl = document.getElementById("source-count");
const promptButtons = document.querySelectorAll(".sample-chip");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function renderSources(sources) {
  sourceCountEl.textContent = String(sources.length);

  if (!sources.length) {
    sourcesEl.className = "sources-empty";
    sourcesEl.textContent = "No product matches yet.";
    return;
  }

  const cards = sources
    .map((source) => {
      const tags = [
        `$${source.price.toFixed(2)}`,
        source.category,
        source.brand,
        `score ${source.score}`,
      ]
        .map((value) => `<span class="meta-pill">${value}</span>`)
        .join("");

      return `
        <article class="source-item">
          <h3>${source.title}</h3>
          <div class="source-meta">${tags}</div>
          <p>${source.description}</p>
        </article>
      `;
    })
    .join("");

  sourcesEl.className = "source-list";
  sourcesEl.innerHTML = cards;
}

async function askCatalog(query, topK) {
  const payload = { query };
  if (topK) {
    payload.top_k = Number(topK);
  }

  const response = await fetch("/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();
  if (query.length < 3) {
    setStatus("Enter at least 3 characters before submitting.", true);
    return;
  }

  submitBtn.disabled = true;
  setStatus("Searching the catalog...");

  try {
    const result = await askCatalog(query, topKInput.value);
    answerEl.className = "";
    answerEl.textContent = result.answer;
    renderSources(result.sources);
    setStatus("Response generated from the demo catalog.");
  } catch (error) {
    answerEl.className = "answer-empty";
    answerEl.textContent = "The request failed. Make sure the FastAPI server is running.";
    renderSources([]);
    setStatus(error.message, true);
  } finally {
    submitBtn.disabled = false;
  }
});

promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query || "";
    queryInput.focus();
  });
});
