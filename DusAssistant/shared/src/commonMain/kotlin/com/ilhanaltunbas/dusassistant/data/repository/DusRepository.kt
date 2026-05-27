package com.ilhanaltunbas.dusassistant.data.repository

import com.ilhanaltunbas.dusassistant.data.remote.DusApiClient

class DusRepository(private val apiClient: DusApiClient) {

    // İleride buraya veritabanı (Room/SQLDelight) eklersen,
    // "Önce yerelden getir, yoksa API'den çek" mantığını tam da bu fonksiyona yazarsın.
    suspend fun getAnswerFromAssistant(question: String): Result<String> {
        return apiClient.askQuestion(question)
    }
}