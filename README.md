\# 🦷 DUS Assistant | AI-Powered Medical Education Platform



!\[Kotlin](https://img.shields.io/badge/kotlin-%237F52FF.svg?style=for-the-badge\&logo=kotlin\&logoColor=white)

!\[Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge\&logo=android\&logoColor=white)

!\[iOS](https://img.shields.io/badge/iOS-000000?style=for-the-badge\&logo=ios\&logoColor=white)

!\[FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge\&logo=fastapi)

!\[Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge\&logo=python\&logoColor=ffdd54)

!\[Claude AI](https://img.shields.io/badge/Claude%20AI-D97757?style=for-the-badge\&logo=anthropic\&logoColor=white)



> A highly reliable, cross-platform smart educational assistant designed for candidates preparing for the Specialization in Dentistry Examination (DUS).



\## 📌 Overview



While Large Language Models (LLMs) offer great potential for personalized education, their tendency to generate incorrect information ("hallucinations") poses a severe risk in clinical study environments. 



\*\*DUS Assistant\*\* eliminates this risk by implementing a robust \*\*Retrieval-Augmented Generation (RAG)\*\* pipeline. The system forces the AI to generate answers \*exclusively\* from verified official textbooks (currently focused on Periodontology), providing a zero-hallucination, fact-based learning experience. 



\## ✨ Key Features



\* \*\*📱 Cross-Platform Excellence:\*\* Fully native UI for both Android and iOS built with Kotlin Multiplatform (KMP) and Compose Multiplatform.

\* \*\*🧠 Zero-Hallucination AI:\*\* Powered by Anthropic's Claude 4.5 and strict guardrails. If the answer isn't in the textbook, the system clearly states it.

\* \*\*⚡ Vector Search Engine:\*\* Millisecond-level clinical context retrieval using Qdrant Vector Database.

\* \*\*💾 Local History:\*\* Persistent, privacy-focused chat history management via Room Database.



\## 🏗️ System Architecture



The project is split into two main components: a high-performance Python/FastAPI backend and a fluid KMP mobile frontend. 



\*(Şema Görselini Buraya Ekleyin)\*

<p align="center">

&#x20; <img src="link\_to\_your\_architecture\_diagram.png" alt="RAG Architecture" width="700">

</p>



\## 📸 Application Interface



\*(Mobil Ekran Görüntülerini Buraya Ekleyin)\*

<p align="center">

&#x20; <img src="link\_to\_ui\_screenshot\_1.png" alt="Main Screen" width="250"> \&nbsp;\&nbsp;\&nbsp;

&#x20; <img src="link\_to\_ui\_screenshot\_2.png" alt="Chat Interface" width="250">

</p>



\## 🛠️ Tech Stack



\*\*Mobile Frontend (KMP):\*\*

\* Kotlin Multiplatform

\* Compose Multiplatform

\* Room Database (Local Storage)

\* Ktor Client (Networking)



\*\*Backend \& AI Pipeline:\*\*

\* Python \& FastAPI

\* LangChain

\* Qdrant (Vector Database)

\* Claude 4.5 Haiku (LLM)

\* OpenAI text-embedding-3-small



\## 👨‍💻 Author



\*\*İlhan Altunbaş\*\* \*Computer Engineering Senior Student\*



\[!\[LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge\&logo=linkedin\&logoColor=white)](https://www.linkedin.com/in/YOUR\_LINKEDIN\_USERNAME)

\[!\[GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/YOUR\_GITHUB\_USERNAME)



\---

\*Developed as a graduation project at Çukurova University.\*

