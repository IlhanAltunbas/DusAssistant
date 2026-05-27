package com.ilhanaltunbas.dusassistant.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

class DusApiClient {

    // Ktor HTTP Client yapılandırması (JSON desteği ile birlikte)
    private val client = HttpClient {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true // API'den fazladan veri gelirse çökmesini engeller
                prettyPrint = true
            })
        }
    }

    // DİKKAT: Buraya kendi güncel Ngrok linkini yapıştırmalısın! (Sonunda '/' OLMAYACAK)
    private val baseUrl = "https://smite-anyone-dividing.ngrok-free.dev"

    // Asenkron olarak soruyu sorup cevabı bekleyen fonksiyon
    suspend fun askQuestion(question: String): Result<String> {
        return try {
            // POST isteği atıyoruz
            val response: AnswerResponse = client.post("$baseUrl/ask") {
                contentType(ContentType.Application.Json)
                setBody(QuestionRequest(soru = question))
            }.body()

            // Gelen JSON'u kontrol ediyoruz
            if (response.durum == "basarili" && response.cevap != null) {
                Result.success(response.cevap)
            } else {
                Result.failure(Exception(response.mesaj ?: "Sunucu bir hata döndürdü."))
            }
        } catch (e: Exception) {
            // İnternet yoksa veya sunucu kapalıysa buraya düşer
            Result.failure(e)
        }
    }
}