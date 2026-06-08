package com.ilhanaltunbas.dusassistant.presentation

import com.ilhanaltunbas.dusassistant.data.repository.DusRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class DusChatViewModel(
    private val repository: DusRepository
) {
    private val viewModelScope = CoroutineScope(Dispatchers.IO)
    private var messageJob: Job? = null

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    init {
        observeSessions()
        initializeChat()
    }

    private fun initializeChat() {
        viewModelScope.launch {
            // Mevcut oturumları bir kez çekelim
            val sessions = repository.getAllSessions().first()
            val latestSession = sessions.firstOrNull()

            // Eğer en son oturum hala boşsa (ismi değişmemişse), onu kullan
            if (latestSession != null && latestSession.title == "Yeni Sohbet") {
                selectSession(latestSession.id)
            } else {
                // Değilse gerçekten yeni bir tane oluştur
                createNewChat()
            }
        }
    }

    private fun observeSessions() {
        viewModelScope.launch {
            repository.getAllSessions().collectLatest { sessions ->
                _uiState.update { it.copy(sessions = sessions) }
            }
        }
    }

    private fun observeMessages(sessionId: Long) {
        messageJob?.cancel() // Eski dinlemeyi iptal et
        messageJob = viewModelScope.launch {
            repository.getMessagesForSession(sessionId).collectLatest { messages ->
                _uiState.update { it.copy(messages = messages) }
            }
        }
    }

    fun createNewChat() {
        viewModelScope.launch {
            val newId = repository.createNewSession()
            _uiState.update { it.copy(currentSessionId = newId, messages = emptyList()) }
            observeMessages(newId)
        }
    }

    fun selectSession(sessionId: Long) {
        _uiState.update { it.copy(currentSessionId = sessionId) }
        observeMessages(sessionId)
    }

    fun sendMessage(userQuery: String) {
        val sessionId = _uiState.value.currentSessionId ?: return
        if (userQuery.isBlank()) return

        viewModelScope.launch {
            // 1. MEVCUT GEÇMİŞİ YAKALA (Yeni soru eklenmeden önceki hali)
            val historyToSend = _uiState.value.messages

            // 2. Eğer bu oturumun ilk mesajıysa başlığı güncelle
            if (historyToSend.isEmpty()) {
                repository.updateSessionTitle(sessionId, userQuery.take(25) + "...")
            }

            // 3. Yeni mesajı veritabanına kaydet (UI Flow üzerinden güncellenecek)
            repository.saveMessage(sessionId, userQuery, isUser = true)
            
            // 4. Yükleniyor durumuna geç
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }

            // 5. API'ye soruyu ve temiz son 10 mesajlık geçmişi gönder
            val limitedHistory = historyToSend.takeLast(10)
            val result = repository.getAnswerFromAssistant(userQuery, limitedHistory)

            result.fold(
                onSuccess = { answer ->
                    repository.saveMessage(sessionId, answer, isUser = false)
                    _uiState.update { it.copy(isLoading = false) }
                },
                onFailure = { error ->
                    _uiState.update { it.copy(
                        isLoading = false,
                        errorMessage = error.message ?: "Bilinmeyen bir hata oluştu."
                    ) }
                }
            )
        }
    }

    fun clearChat() {
        // Bu artık sadece aktif oturumu değil, tüm geçmişi temizler (isteğine göre değişebilir)
        viewModelScope.launch {
            repository.clearAllHistory()
            createNewChat()
        }
    }
    
    fun deleteSession(sessionId: Long) {
        viewModelScope.launch {
            repository.deleteSession(sessionId)
            if (_uiState.value.currentSessionId == sessionId) {
                createNewChat()
            }
        }
    }
}
