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
const stageIndicator =
    document.getElementById("stage-indicator");

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

    addMessage(
        "AI",
        "Connecting to interviewer..."
    );

    try {
        const response =
            await fetch(
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

        const data =
            await response.json();

        messages.innerHTML = "";

        interviewId =
            data.interview_id;

        updateStage(
            data.stage
        );

        addMessage(
            "AI",
            data.question
        );
    }

    catch (error) {
        console.error(error);

        addMessage(
            "AI",
            "Failed to connect."
        );
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