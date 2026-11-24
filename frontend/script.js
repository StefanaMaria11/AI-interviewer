console.log("SCRIPT LOADED");
const API_URL = "http://localhost:8000";

let interviewId = null;
let interviewFinished = false;

const startButton = document.getElementById("start-button");
const sendButton = document.getElementById("send-button");
const answerInput = document.getElementById("answer-input");
const welcomeModal = document.getElementById("welcome-modal");
const chatContainer = document.getElementById("chat-container");
const messages = document.getElementById("messages");
const loadingModal = document.getElementById("loading-modal");
const summaryModal = document.getElementById("summary-modal");
const summaryText = document.getElementById("summary-text");
const exitButton = document.getElementById("exit-button");
const stageIndicator = document.getElementById("stage-indicator");
const feedbackButton = document.getElementById("feedback-button");
const feedbackStatus = document.getElementById("feedback-status");
const feedbackContainer = document.getElementById("feedback-container");
const feedbackStrengths = document.getElementById("feedback-strengths");
const feedbackImprovements = document.getElementById("feedback-improvements");
const feedbackOverall = document.getElementById("feedback-overall");

startButton.addEventListener(
    "click",
    startInterview
);

sendButton.addEventListener(
    "click",
    sendAnswer
);

answerInput.addEventListener(
    "keydown",
    event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendAnswer();
        }
    }
);

feedbackButton.addEventListener("click", generateFeedback);

exitButton.addEventListener(
    "click",
    () => {
        document.body.innerHTML = `
            <h2 style="
                text-align:center;
                margin-top:100px;
            ">
                You can close this tab.
            </h2>
        `;
    }
);


async function startInterview() {
    welcomeModal.classList.add("hidden");
    chatContainer.classList.remove("hidden");

    messages.replaceChildren();
    showTypingIndicator();

    try {
        const response = await fetch(
            `${API_URL}/start-interview`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    topic: "AI Engineering Intern"
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        if (!data.interview_id || !data.question) {
            throw new Error("The server did not return a question.");
        }

        interviewId = data.interview_id;
        updateStage(data.stage);

        removeTypingIndicator();
        addMessage("AI", data.question);

        answerInput.focus();

    } catch (error) {
        console.error("Failed to start interview:", error);

        removeTypingIndicator();

        addMessage(
            "AI",
            "I couldn't prepare the first question. Please try again."
        );

        const retryButton = document.createElement("button");
        retryButton.textContent = "Try again";
        retryButton.addEventListener("click", startInterview);
        messages.appendChild(retryButton);
    }
}


async function sendAnswer() {
    if (interviewFinished)
        return;

    const answer =
        answerInput.value.trim();

    if (!answer)
        return;

    addMessage(
        "You",
        answer
    );

    answerInput.value = "";
    answerInput.disabled = true;
    sendButton.disabled = true;

    showTypingIndicator();

    try {
        const response =
            await fetch(
                `${API_URL}/interview/${interviewId}/answer`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        answer
                    })
                }
            );

        const data =
            await response.json();

        removeTypingIndicator();

        answerInput.disabled = false;
        sendButton.disabled = false;

        if (data.stage) {
            updateStage(
                data.stage
            );
        }

        if (data.question) {
            addMessage(
                "AI",
                data.question
            );
        }

        if (data.summary_available) {
            finishInterview();
        }
    }

    catch (error) {
        console.error(error);

        removeTypingIndicator();

        answerInput.disabled = false;
        sendButton.disabled = false;

        addMessage(
            "AI",
            "Something went wrong."
        );
    }
}

async function finishInterview() {
    interviewFinished = true;

    chatContainer.classList.add("hidden");

    loadingModal.classList.remove("hidden");

    try {
        const response =
            await fetch(
                `${API_URL}/interview/${interviewId}/summary`
            );

        const data =
            await response.json();

        summaryText.textContent =
            data.summary;
    }

    catch (error) {
        summaryText.textContent =
            "Could not generate summary.";
    }

    loadingModal.classList.add("hidden");
    summaryModal.classList.remove("hidden");
}

function addMessage(sender, text) {
    const message =
        document.createElement("div");

    message.classList.add(
        "message"
    );

    message.classList.add(
        sender === "AI"
            ? "ai-message"
            : "user-message"
    );

    const bubble =
        document.createElement("div");

    bubble.classList.add(
        "bubble"
    );

    const title =
        document.createElement("strong");

    title.textContent =
        sender;

    const paragraph =
        document.createElement("p");

    paragraph.textContent =
        text;

    bubble.appendChild(title);
    bubble.appendChild(paragraph);

    message.appendChild(bubble);
    messages.appendChild(message);
    messages.scrollTop =
        messages.scrollHeight;
}

function updateStage(stage) {
    if (stageIndicator) {
        stageIndicator.textContent =
            stage
                .replaceAll("_", " ")
                .toLowerCase();
    }
}

function showTypingIndicator() {
    const typing =
        document.createElement("div");

    typing.id =
        "typing-indicator";

    typing.classList.add(
        "message",
        "ai-message"
    );

    typing.innerHTML = `
        <div class="bubble typing-bubble">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

    messages.appendChild(typing);
    messages.scrollTop =
        messages.scrollHeight;
}

function removeTypingIndicator() {
    const typing =
        document.getElementById(
            "typing-indicator"
        );

    if (typing) {
        typing.remove();
    }
}

async function generateFeedback() {
    feedbackButton.disabled = true;
    feedbackStatus.textContent = "Generating feedback...";

    try {
        const response = await fetch(
            `${API_URL}/interview/${interviewId}/feedback`,
            { method: "POST" }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const feedback = data.feedback;

        renderFeedbackPoints(
            feedbackStrengths,
            feedback.strengths
        );

        renderFeedbackPoints(
            feedbackImprovements,
            feedback.improvements
        );

        feedbackOverall.textContent = feedback.overall_feedback;

        feedbackContainer.classList.remove("hidden");
        feedbackButton.classList.add("hidden");
        feedbackStatus.textContent = "";

    } catch (error) {
        console.error(error);
        feedbackStatus.textContent =
            "Could not generate feedback. Please try again.";
        feedbackButton.disabled = false;
    }
}

function renderFeedbackPoints(container, points) {
    container.replaceChildren();

    if (points.length === 0) {
        container.textContent = "No observations available.";
        return;
    }

    points.forEach(point => {
        const item = document.createElement("div");
        item.className = "feedback-point";

        const observation = document.createElement("h4");
        observation.textContent = point.observation;

        const evidence = document.createElement("p");
        evidence.className = "feedback-evidence";

        const fullEvidence = point.evidence;
        const maxLength = 220;

        const isLong = fullEvidence.length > maxLength;

        const preview = isLong
            ? fullEvidence.slice(0, maxLength).trimEnd() + "..."
            : fullEvidence;

        evidence.textContent = `Evidence: "${preview}"`;

        item.append(observation, evidence);

        if (isLong) {
            const toggleButton = document.createElement("button");
            toggleButton.type = "button";
            toggleButton.className = "evidence-toggle";
            toggleButton.textContent = "Show more";
            toggleButton.setAttribute("aria-expanded", "false");

            let expanded = false;

            toggleButton.addEventListener("click", () => {
                expanded = !expanded;

                evidence.textContent = expanded
                    ? `Evidence: "${fullEvidence}"`
                    : `Evidence: "${preview}"`;

                toggleButton.textContent = expanded
                    ? "Show less"
                    : "Show more";

                toggleButton.setAttribute(
                    "aria-expanded",
                    String(expanded)
                );
            });

            item.appendChild(toggleButton);
        }


        if (point.suggestion) {
            const suggestion = document.createElement("p");
            suggestion.textContent = `Suggestion: ${point.suggestion}`;
            item.appendChild(suggestion);
        }

        container.appendChild(item);
    });
}