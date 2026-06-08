package com.ilhanaltunbas.dusassistant.data.repository

import com.ilhanaltunbas.dusassistant.data.local.ChatSessionEntity
import com.ilhanaltunbas.dusassistant.data.local.DusDao
import com.ilhanaltunbas.dusassistant.data.local.MessageEntity
import com.ilhanaltunbas.dusassistant.data.remote.DusApiClient
import com.ilhanaltunbas.dusassistant.presentation.ChatMessage
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.datetime.Clock

data class ChatSession(
    val id: Long,
    val title: String,
    val timestamp: Long
)

class DusRepository(
    private val apiClient: DusApiClient,
    private val dusDao: DusDao
) {

    // Tüm Oturumları Getir
    fun getAllSessions(): Flow<List<ChatSession>> {
        return dusDao.getAllSessions().map { entities ->
            entities.map { entity ->
                ChatSession(entity.id, entity.title, entity.timestamp)
            }
        }
    }

    // Yeni Oturum Başlat
    suspend fun createNewSession(title: String = "Yeni Sohbet"): Long {
        val session = ChatSessionEntity(
            title = title,
            timestamp = Clock.System.now().toEpochMilliseconds()
        )
        return dusDao.insertSession(session)
    }

    // Belirli bir oturumun mesajlarını getir
    fun getMessagesForSession(sessionId: Long): Flow<List<ChatMessage>> {
        return dusDao.getMessagesForSession(sessionId).map { entities ->
            entities.map { entity ->
                ChatMessage(
                    text = entity.text,
                    isUser = entity.isUser
                )
            }
        }
    }

    // Mesajı oturuma kaydet
    suspend fun saveMessage(sessionId: Long, text: String, isUser: Boolean) {
        val entity = MessageEntity(
            sessionId = sessionId,
            text = text,
            isUser = isUser,
            timestamp = Clock.System.now().toEpochMilliseconds()
        )
        dusDao.insertMessage(entity)

        // Eğer ilk mesaj ise oturum başlığını güncelle (Opsiyonel)
        // Burada basitçe ilk mesajın bir kısmını başlık yapabiliriz
    }

    // Oturum Başlığını Güncelle
    suspend fun updateSessionTitle(sessionId: Long, title: String) {
        dusDao.updateSessionTitle(sessionId, title)
    }

    // API'den cevap al (Backend'in beklediği "User: ..." formatı ile)
    suspend fun getAnswerFromAssistant(question: String, history: List<ChatMessage>): Result<String> {
        val formattedHistory = history.map { 
            if (it.isUser) "User: ${it.text}" else "Assistant: ${it.text}"
        }
        return apiClient.askQuestion(question, formattedHistory)
    }

    suspend fun deleteSession(sessionId: Long) {
        dusDao.deleteSession(sessionId)
    }

    suspend fun clearAllHistory() {
        dusDao.clearAllHistory()
    }
}
