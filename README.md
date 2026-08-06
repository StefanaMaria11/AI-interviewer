# AI Interviewer

A lightweight AI-powered interview application built with FastAPI, a simple web interface, and a locally running LLM.

The project was created as a solution for the "Mini AI Interviewer" assignment. The goal was to build an application that can conduct short AI-powered interviews on a selected topic, collect user answers, and generate a final summary based on the conversation.

The application focuses on creating a structured interview experience where the AI acts as an interviewer while keeping a predictable flow and clear separation between the AI logic and the application logic.

## Project Overview

The application allows users to:

- start an interview session
- answer AI-generated questions interactively through the UI
- follow a structured interview flow
- receive an AI-generated summary at the end
- store the complete interview transcript and analysis

The interview topic and structure are defined by the application configuration. The user does not need to provide a topic; instead, the AI interviewer is guided by predefined instructions and interview stages.

The project uses a local LLM through Ollama instead of relying on an external API. This decision was made to experiment with running AI applications in a more controlled environment and to avoid sending user data to external services.

# Motivation and Project Idea

Instead of choosing one of the example topics provided in the assignment, I decided to build a more realistic use case: an AI interviewer for a job interview scenario.

The reason behind this decision was that I wanted to work on a project that could represent a real-world application rather than only a technical demonstration. I was also inspired by the interview approaches used by some companies, such as AI-based preliminary interviews, where candidates can interact with an automated system before reaching the next recruitment stage.

Personally, I still believe that human interaction is an important part of the interview process, especially for understanding communication skills and personality. However, when a company receives a large number of applications, an AI interviewer could become a useful tool for an initial screening stage by helping recruiters identify relevant candidates faster.

Another reason for choosing this idea was that I prefer building projects that feel realistic and can be continuously improved. Instead of creating a one-time prototype, I wanted to design a foundation that could evolve with additional features, such as different interview types, improved candidate analysis, better evaluation methods, or integration into a larger recruitment workflow.

## Structured Interview Flow

One of the main decisions in this project was choosing to run the LLM locally instead of using a cloud-based provider.

My first option was to use a hosted model such as OpenAI models, because they generally provide better reasoning capabilities and more consistent responses. However, this approach requires API costs and depends on an external service.

Since I wanted to experiment with a fully local AI application, I decided to use Ollama instead. Another important constraint was the available hardware. The project was developed on an older laptop with limited computational resources, which made running larger state-of-the-art open-source models impractical.

Because of this limitation, I selected a smaller pretrained model that could run locally while still being able to handle the requirements of this project. The chosen model provides a good balance between response quality and resource consumption, although larger models would likely provide better interview questions and more detailed summaries.

Alternatively, for a production system where infrastructure and budget allow it, I would consider using hosted models through providers such as OpenAI, Anthropic, or other enterprise LLM providers, because they offer stronger reasoning capabilities, better reliability, and easier scalability.

The current implementation was therefore a compromise between AI quality, hardware limitations, cost, and the goal to complete the task.

# Architecture

The application was designed with a simple layered architecture, separating the user interface, backend logic, AI interaction, and data persistence.

The main components are:

- Frontend: responsible for user interaction and displaying the interview flow
- Backend API: manages the application logic and communication between components
- Interview Service: controls the interview state and question generation process
- LLM Service: handles communication with the local language model
- Storage Service: persists interview transcripts and generated summaries

The different components are containerized using Docker and connected through Docker Compose. Each service runs in its own isolated environment, while Docker Compose manages the communication between containers and simplifies the setup process.

The current architecture consists of three main containers:

- Frontend container: serves the web interface
- Backend container: runs the FastAPI application and handles the interview logic
- Ollama container: provides the locally running LLM service

## Application Flow

1. User starts interview
        |
2. Backend initializes interview session
        |
3. Current interview stage is identified
        |
4. LLM generates the next question
        |
5. User provides answer
        |
6. Answer is stored
        |
7. Process repeats until all stages are completed
        |
8. LLM generates final summary
        |
9. Transcript and summary are saved

# Project Structure

The project is organized into separate components to keep the application logic, AI interaction, and user interface independent.


Main responsibilities:

- `main.py` - serves as the entry point of the FastAPI application. It initializes the API, defines the available endpoints, and connects the different services together.
- `models/` - contains the data models used by the application
- `interviewer_service.py` - manages the interview stages and interaction logic
- `llm_service.py` - handles communication with the local LLM through Ollama
- `storage_service.py` - manages saving and loading interview data
- `prompts/` - stores the prompts used for question generation and summarization
- `frontend/` - provides the user interface
- `docker-compose.yml` - defines and connects the application services

# AI Integration and Prompt Design

The AI component is the core of this application, as the goal was not only to generate questions, but to create a structured interview experience where the LLM behaves as an interviewer.

The interaction with the LLM is handled through a dedicated `LLMService`, while the prompt creation logic is separated from the application logic. This allows the AI behavior to be improved independently without modifying the interview workflow.

---

## Prompt Design

One of the main challenges was controlling the behavior of a general-purpose LLM. Without clear instructions, the model could generate unrelated questions, skip interview topics, repeat information, or change the difficulty level unpredictably.

To address this, I designed a layered prompt structure consisting of:

- interviewer role definition
- global interview rules
- current interview stage instructions
- previous conversation context

The final prompt sent to the LLM contains:
 - Interviewer Role
 - Question Generation Rules
 - Current Interview Stage
 - Stage-specific Instructions
 - Previous Conversation

 
This approach gives the model enough context to generate adaptive questions while still keeping the interview controlled.

## Structured Stage-Based Prompting

Instead of allowing the LLM to freely decide the interview direction, each question belongs to a predefined stage:
1. BACKGROUND
2. MOTIVATION
3. EXPERIENCE
4. TECHNICAL FOUNDATION
5. PROBLEM SOLVING
6. SUMMARY

Each stage contains specific instructions about:

- what information should be collected
- what topics should be explored
- what topics should be avoided
- examples of good and bad questions

For example, during the technical foundation stage, the system first checks previous experience answers. If the candidate already mentioned an AI-related project, the model is instructed to ask about that specific experience instead of introducing unrelated theoretical questions.

This creates a more realistic interview experience because the conversation builds on the candidate's previous answers.

## Controlling LLM Output

The prompts include explicit constraints to improve consistency:

- generate exactly one question
- focus only on the current stage
- avoid combining multiple questions
- avoid greetings or additional explanations
- do not repeat information already provided

These constraints reduce unpredictable outputs and make the AI behavior easier to evaluate.

## Conversation Context Management

The application does not send only the latest answer to the LLM. Instead, the previous interview conversation is reconstructed and included as context.

This allows the model to:

- avoid repeating questions
- ask relevant follow-ups
- connect new questions with previous answers
- adapt based on the candidate's experience level

## Interview Summary Generation

After all interview stages are completed, the same LLM-based approach is used to generate a final candidate summary.

The summary prompt is designed to keep the evaluation objective by:

- using only information explicitly mentioned by the candidate
- avoiding exaggerated descriptions
- avoiding assumptions about skills or experience
- preventing the model from making hiring decisions

The generated summary focuses on:

- background
- motivation
- technical experience
- problem-solving approach
- overall suitability for an AI Engineering Intern role


## Additional Analysis

Besides the LLM-generated summary, the application performs lightweight analysis of the candidate's answers.

The analysis includes:

### Keyword Extraction

A simple keyword extraction mechanism identifies relevant concepts mentioned by the candidate.

Technical terms receive a higher score to prioritize keywords related to software engineering and AI topics.

### Sentiment Analysis

A rule-based sentiment analysis is also performed to identify the general tone of the candidate's answers.

The result can be:

- positive
- negative

This is intentionally kept simple because the main purpose of the project was the AI interviewer workflow rather than building a complete NLP evaluation system.

# Running the Application

The application is fully containerized using Docker Compose, which manages the frontend, backend, and local LLM services.

## Prerequisites

Before running the application, make sure you have:

- Docker installed
- Docker Compose installed
- enough resources available for running the local LLM

The project was developed and tested on a local machine using Docker Desktop.

---

## Starting the Application

After extracting the project archive, navigate to the project root folder:

```bash
cd ai-interviewer
```
- Start all services using:

```bash
docker compose up --build
```
 - In another terminal:

```bash
 docker exec -it ollama
```

```bash
ollama pull gemma3:1b
```
- In your browser type the following for testing: http://localhost:5000

- To stop all running containers:
```bash
docker compose down
```

# Usage Notes and Limitations

## Application Usage Flow

Each time the application is opened, a new interview session is automatically initialized.

The user should first read the information provided in the popup window before starting the interview. After starting the interview, the AI interviewer guides the candidate through the predefined interview stages.

At the end of the interview:

- the candidate receives an AI-generated summary directly in the user interface
- the complete interview transcript and additional analysis are stored locally

The analysis generated by the application (keywords extraction and sentiment analysis) is not displayed to the candidate through the frontend. It is stored internally together with the interview data in: /data/interviews

## Known Limitations

The current implementation was designed as a functional prototype, therefore some limitations are still present.

### Local Data Persistence

Interview data is currently stored as JSON files.

When running the application multiple times, existing interview files may be overwritten instead of being managed as separate historical sessions.

A production-ready implementation would replace this approach with a database solution and include:

- unique interview identifiers
- persistent history management
- candidate session management
- better data organization

### LLM Consistency

Because the application relies on a local language model, there are rare situations where the model may lose track of the exact interview context or become slightly confused between consecutive questions.

This can happen especially when:

- previous answers are very short
- multiple topics are mentioned in the same answer
- the local model has limited reasoning capabilities

A larger language model would likely improve consistency and context understanding.

Further improvements could include:

- using a larger pretrained model
- fine-tuning the model for interview scenarios
- improving evaluation datasets for prompt optimization
- adding additional validation layers before displaying generated questions

### Prototype Scope

The current version focuses on demonstrating the AI interviewer workflow and the interaction between software components and an LLM.

Additional features that could be implemented in a production version include:

- user authentication
- recruiter dashboard
- database persistence
- multiple interview templates
- candidate comparison tools
- improved AI-based evaluation methods