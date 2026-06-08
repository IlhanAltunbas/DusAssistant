
# DUS Assistant: RAG-Based Educational Assistant for Medical Specialization

<p>
  <img src="https://img.shields.io/badge/kotlin-%237F52FF.svg?style=for-the-badge&logo=kotlin&logoColor=white" alt="Kotlin" />
  <img src="https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android" />
  <img src="https://img.shields.io/badge/iOS-000000?style=for-the-badge&logo=ios&logoColor=white" alt="iOS" />
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/Claude%20AI-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Claude AI" />
</p>

## Abstract

This repository contains the source code for **DUS Assistant**, an academic graduation project developed to address the limitations of Large Language Models (LLMs) in medical education. By implementing a strict Retrieval-Augmented Generation (RAG) architecture, the system provides referenced, factually accurate answers to candidates preparing for the Specialization in Dentistry Examination (DUS), specifically utilizing Periodontology textbooks as the primary knowledge base.

## System Architecture

The project is engineered with a strict separation of concerns, dividing the cross-platform client and the AI-driven backend:

* **Mobile Client:** Built with Kotlin Multiplatform (KMP) and Compose Multiplatform, ensuring native performance and a unified codebase across Android and iOS environments.
* **Backend & RAG Pipeline:** Developed with FastAPI and Python. It integrates Qdrant as a vector database for high-speed semantic search and utilizes Anthropic's Claude 4.5 LLM for context-aware, clinically grounded response generation.

<p align="center">
  <img width="803" height="523" alt="Ekran görüntüsü 2026-05-30 170515" src="https://github.com/user-attachments/assets/22d05c43-299c-498a-af08-96598d151413" />
</p>

## Core Capabilities

* **Hallucination Prevention:** Strict prompt engineering and RAG constraints ensure the AI generates responses solely from official textbook contexts.
* **Cross-Platform UI:** Seamless user experience across mobile platforms with a shared presentation logic.
* **Persistent Local Storage:** Efficient chat history management utilizing Room Database within the KMP ecosystem.
* **Optimized Vector Retrieval:** Millisecond-level document chunk retrieval via text-embedding-3-small and Qdrant vector spaces.

## Application Interfaces

<p align="center">
   <img width="250" alt="Chat History" src="https://github.com/user-attachments/assets/175d21a5-3b90-4e00-b754-b5bbfb4ef78c" />
   <img width="250" alt="Application Main Screen" src="https://github.com/user-attachments/assets/d11b8fe8-87b0-4691-aa2d-f5f93e19d320" />
   <img width="250"  alt="Chat Interface Demonstrating RAG" src="https://github.com/user-attachments/assets/a910c2a6-019d-4379-8879-20c7b932726b" />
</p>

## Author

**İlhan Altunbaş**
*B.Sc. Computer Engineering*

<p>
  <a href="https://www.linkedin.com/in/ilhanaltunbas/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
  <a href="https://github.com/IlhanAltunbas"><img src="https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
</p>

---
*Developed as a senior graduation project at Çukurova University, Computer Engineering Department.*
