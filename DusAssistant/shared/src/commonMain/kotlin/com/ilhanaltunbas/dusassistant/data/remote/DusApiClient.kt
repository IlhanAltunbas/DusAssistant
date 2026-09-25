package com.ilhanaltunbas.dusassistant.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
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
            val response: AnswerResponse = client.post("$baseUrl/ask") {
                contentType(ContentType.Application.Json)
                setBody(QuestionRequest(soru = question, gecmis = history))
            }.body()

            if (response.answer != null) {
                Result.success(response.answer)
            } else {
                Result.failure(Exception("Sunucudan boş cevap geldi."))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}