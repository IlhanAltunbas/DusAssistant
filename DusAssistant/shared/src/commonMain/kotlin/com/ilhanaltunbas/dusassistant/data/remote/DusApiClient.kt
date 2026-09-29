package com.ilhanaltunbas.dusassistant.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

class DusApiClient {

    private val client = HttpClient {
        install(HttpTimeout) {
            requestTimeoutMillis = 90_000
            connectTimeoutMillis = 90_000
            socketTimeoutMillis = 90_000
        }
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                prettyPrint = true
            })
        }
        install(Logging) {
            level = LogLevel.BODY
            // BODY seviyesi header'ları da yazar; anahtar Logcat'e düşmesin.
            sanitizeHeader { header -> header == API_KEY_HEADER }
            logger = object : Logger {
                override fun log(message: String) {
                    println("HTTP Log: $message")
                }
            }
        }
    }

    private val baseUrl = "https://dus-backend.wittysand-a01d0f70.francecentral.azurecontainerapps.io"

    suspend fun askQuestion(question: String, history: List<String>): Result<String> {
        return try {
            val response = client.post("$baseUrl/ask") {
                header(API_KEY_HEADER, ApiConfig.API_KEY)
                contentType(ContentType.Application.Json)
                setBody(QuestionRequest(soru = question, gecmis = history))
            }
            // Gateway hatalarında gövde JSON olmayabilir; o durumda null kalır.
            val govde = runCatching { response.body<AnswerResponse>() }.getOrNull()

            when {
                // 401/429 gibi durumlarda backend'in mesajı (örn. "Çok fazla soru gönderdin.") gösterilir.
                !response.status.isSuccess() -> Result.failure(
                    Exception(govde?.detail ?: "Sunucu hatası (${response.status.value}), lütfen daha sonra tekrar dene.")
                )
                govde?.answer != null -> Result.success(govde.answer)
                else -> Result.failure(Exception("Sunucudan boş cevap geldi."))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private companion object {
        const val API_KEY_HEADER = "X-API-Key"
    }
}