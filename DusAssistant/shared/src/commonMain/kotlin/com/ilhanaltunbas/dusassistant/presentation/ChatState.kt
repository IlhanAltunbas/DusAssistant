package com.ilhanaltunbas.dusassistant.presentation

// Tekil mesaj modeli
data class ChatMessage(
    val text: String,
    val isUser: Boolean // Kullanıcı sağda, asistan solda görünsün diye
)

// Ekranın genel durumu
data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)