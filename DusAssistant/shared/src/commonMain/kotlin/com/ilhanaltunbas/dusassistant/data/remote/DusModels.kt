package com.ilhanaltunbas.dusassistant.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Backend'in beklediği tam yapı
@Serializable
data class QuestionRequest(
    @SerialName("question") val soru: String,
    @SerialName("history") val gecmis: List<String> = emptyList()
)

// Backend'in döndürdüğü tam yapı
@Serializable
data class AnswerResponse(
    @SerialName("answer") val answer: String? = null
)
