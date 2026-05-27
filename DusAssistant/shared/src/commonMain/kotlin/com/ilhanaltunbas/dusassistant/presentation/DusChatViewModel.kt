package com.ilhanaltunbas.dusassistant.presentation

import com.ilhanaltunbas.dusassistant.data.repository.DusRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class DusChatViewModel(
    private val repository: DusRepository
) {
    // KMP'de asenkron işlemleri yönetecek Coroutine kapsamı
    private val viewModelScope = CoroutineScope(Dispatchers.IO)

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    fun sendMessage(userQuery: String) {
        if (userQuery.isBlank()) return

        // 1. Kullanıcı mesajını ekle ve Yükleniyor'a geç
        _uiState.update { currentState ->
            currentState.copy(
                messages = currentState.messages + ChatMessage(text = userQuery, isUser = true),
                isLoading = true,
                errorMessage = null
            )
        }

        // 2. Arka planda FastAPI'ye soruyu gönder
        viewModelScope.launch {
            val result = repository.getAnswerFromAssistant(userQuery)

            result.fold(
                onSuccess = { answer ->
                    // 3. Cevap gelirse asistan mesajı olarak ekle ve Yükleniyor'u kapat
                    _uiState.update { currentState ->
                        currentState.copy(
                            messages = currentState.messages + ChatMessage(text = answer, isUser = false),
                            isLoading = false
                        )
                    }
                },
                onFailure = { error ->
                    // 4. Hata olursa hatayı ekrana yansıt
                    _uiState.update { currentState ->
                        currentState.copy(
                            isLoading = false,
                            errorMessage = error.message ?: "Bilinmeyen bir hata oluştu."
                        )
                    }
                }
            )
        }
    }
}