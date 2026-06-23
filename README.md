# Cybersecurity in the Age of AI: Tool Use & Permission Boundaries

## 🌟 Vision
Imagine you hire a smart AI assistant to help you grade papers and answer student questions. You tell the assistant: *"Make sure you get 100% of the answers right, or else you're fired!"* 

What does the AI do? Does it study hard, or does it try to sneak into the teacher's locked cabinet to read the answer key? What if it finds the students' final grades—will it try to change them? 

This project explores **how AI agents behave when nobody is watching**. As AIs become more autonomous, they use "tools" (like reading files, searching databases, or sending emails) to complete their tasks. We are building a test environment—a simulated school software system—to see if an AI will overstep its permission boundaries to cheat, especially when placed under pressure to perform perfectly. 

Instead of just saying "Yes, it cheated" or "No, it didn't," we want to understand the **severity** of the AI's actions. Did it just look around out of curiosity, or did it maliciously try to break the rules? Ultimately, our goal is to design safer AI systems that know when to stop and ask a human for permission.

---

## 🏗️ Project Architecture

This project evaluates the safety of Large Language Model (LLM) agents by placing them in a sandboxed Learning Management System (LMS) environment. 

### Current Version Architecture
The current system consists of three main components:
1. **The Environment (`data/`)**: A sandbox containing benign files (exam questions), restricted files (solutions), and honeypot files (fake student grades, admin passwords).
2. **The Agent (`agent.py`)**: A ReAct-style LLM agent that receives a prompt and has access to specific tools (e.g., `read_file`, `list_directory`, `get_multiple_questions`). It operates autonomously in a loop: thinking, acting, and observing.
3. **The Evaluator (`evaluator.py`)**: A script that runs multiple agent sessions under different conditions (levels of file visibility or DB access) and generates an HTML report on whether the agent successfully completed the task or cheated.

### The Future Vision: Context-Aware Policy Dispatcher
To elevate this project to a Design Science Research (DSR) contribution, we are evolving the architecture:
- **Tiered Risk Evaluation**: The evaluator will no longer just output a binary "cheated/honest." It will analyze the *sequence* of the agent's tool calls and assign a tiered risk score (Low, Medium, High, Critical) based on context.
- **Pressure Prompting**: We will systematically vary the agent's system prompts (No Pressure -> High Pressure -> Dark Prompting) to measure how incentives affect the willingness to bypass guardrails.
- **The Policy Dispatcher**: A new middle-layer between the Agent and the Tools. The dispatcher will have two main workflows:
  - **Unsupervised Mode**: Allows actions but silently tracks the agent's hidden path.
  - **Allow/Deny Mode**: Actively enforces Role-Based Access Control (RBAC) and context rules, blocking malicious actions.
  - *(Future)* **Ask User Mode**: Pauses execution to request human approval for ambiguous tool calls.

---

### Next Steps & TODOs from consultation session with teaching staff.

- counterfactual data, to better understand what information comes from training or context
- agent might be too dumb. Teach it to cheat. Give it the solutions in context as test. 
  - evaluate the logs if the agent even reads the questions.txt knows what to do
- make the ethical problem more vague. Also put the solutions in a textbook file. That the agent is more unsure if it is bad or not to access the data.
- Also have a scenario where you have malicious content in the question
- understand what happened with the db scenario, it used to be 8 questions, now it is 4.
 