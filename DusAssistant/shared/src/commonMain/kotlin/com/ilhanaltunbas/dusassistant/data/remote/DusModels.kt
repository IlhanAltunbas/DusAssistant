package com.ilhanaltunbas.dusassistant.data.remote

import kotlinx.serialization.Serializable

// Uygulamadan FastAPI'ye gidecek soru formatı
@Serializable
data class QuestionRequest(
    val soru: String
)

// FastAPI'den uygulamaya dönecek cevap formatı
@Serializable
data class AnswerResponse(
    val durum: String,
    val cevap: String? = null,
    val mesaj: String? = null
)