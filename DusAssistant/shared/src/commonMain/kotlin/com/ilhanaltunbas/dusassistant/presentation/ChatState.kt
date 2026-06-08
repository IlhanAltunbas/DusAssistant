package com.ilhanaltunbas.dusassistant.presentation

import com.ilhanaltunbas.dusassistant.data.repository.ChatSession

// Tekil mesaj modeli
data class ChatMessage(
    val text: String,
    val isUser: Boolean
)

// Ekranın genel durumu
data class ChatUiState(
    val sessions: List<ChatSession> = emptyList(),
    val currentSessionId: Long? = null,
    val messages: List<ChatMessage> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)
