package com.ilhanaltunbas.dusassistant.data.remote

import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.MockRequestHandleScope
import io.ktor.client.engine.mock.respond
import io.ktor.client.engine.mock.toByteArray
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class DusApiClientTest {

    private val jsonBaslik = headersOf(HttpHeaders.ContentType, "application/json")

    // Sahte sunucu: her isteği kaydeder ve verilen cevabı döner. Ağa çıkılmaz.
    private class SahteSunucu(
        val cevap: suspend MockRequestHandleScope.(HttpRequestData) -> HttpResponseData,
    ) {
        val istekler = mutableListOf<HttpRequestData>()
        val engine = MockEngine { istek ->
            istekler += istek
            cevap(istek)
        }
    }

    private fun sunucu(durum: HttpStatusCode, govde: String) = SahteSunucu {
        respond(govde, durum, jsonBaslik)
    }

    // -----------------------------------------------------------------------
    // İstek
    // -----------------------------------------------------------------------

    @Test
    fun soruyu_anahtarla_ve_gecmisle_ask_endpointine_gonderir() = runTest {
        val sahte = sunucu(HttpStatusCode.OK, """{"answer": "Cevap"}""")

        DusApiClient(sahte.engine).askQuestion("Gingivitis nedir?", listOf("User: Merhaba"))

        val istek = sahte.istekler.single()
        assertEquals(HttpMethod.Post, istek.method)
        assertEquals("/ask", istek.url.encodedPath)
        assertEquals(ApiConfig.API_KEY, istek.headers["X-API-Key"])

        val govde = Json.parseToJsonElement(istek.body.toByteArray().decodeToString()).jsonObject
        assertEquals("Gingivitis nedir?", govde["question"]?.jsonPrimitive?.content)
        assertEquals(listOf("User: Merhaba"), govde["history"]?.jsonArray?.map { it.jsonPrimitive.content })
    }

    // -----------------------------------------------------------------------
    // Başarılı cevap
    // -----------------------------------------------------------------------

    @Test
    fun basarili_cevapta_answer_doner() = runTest {
        val sahte = sunucu(HttpStatusCode.OK, """{"answer": "Gingivitis diş eti iltihabıdır."}""")

        val sonuc = DusApiClient(sahte.engine).askQuestion("Gingivitis nedir?", emptyList())

        assertEquals("Gingivitis diş eti iltihabıdır.", sonuc.getOrNull())
    }

    @Test
    fun bilinmeyen_alanlar_cevabi_bozmaz() = runTest {
        // Backend ileride yeni alan eklerse eski uygulama sürümleri çalışmaya devam etmeli.
        val sahte = sunucu(HttpStatusCode.OK, """{"answer": "Cevap", "sources": ["kitap.pdf"]}""")

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertEquals("Cevap", sonuc.getOrNull())
    }

    @Test
    fun answer_yoksa_hata_doner() = runTest {
        val sahte = sunucu(HttpStatusCode.OK, "{}")

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertEquals("Sunucudan boş cevap geldi.", sonuc.exceptionOrNull()?.message)
    }

    // -----------------------------------------------------------------------
    // Hatalar: backend'in mesajı ("detail") kullanıcıya gösterilir, cevap olarak dönmez.
    // Cevap dönseydi ViewModel onu asistan mesajı diye sohbet geçmişine kaydederdi.
    // -----------------------------------------------------------------------

    @Test
    fun yanlis_anahtarda_backend_mesaji_hata_olarak_doner() = runTest {
        val sahte = sunucu(HttpStatusCode.Unauthorized, """{"detail": "Geçersiz veya eksik API anahtarı."}""")

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertTrue(sonuc.isFailure)
        assertEquals("Geçersiz veya eksik API anahtarı.", sonuc.exceptionOrNull()?.message)
    }

    @Test
    fun istek_sinirinda_backend_mesaji_hata_olarak_doner() = runTest {
        val sahte = sunucu(
            HttpStatusCode.TooManyRequests,
            """{"detail": "Çok fazla soru gönderdin. Lütfen daha sonra tekrar dene."}""",
        )

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertEquals("Çok fazla soru gönderdin. Lütfen daha sonra tekrar dene.", sonuc.exceptionOrNull()?.message)
    }

    @Test
    fun gecici_llm_hatasinda_503_mesaji_hata_olarak_doner() = runTest {
        val sahte = sunucu(
            HttpStatusCode.ServiceUnavailable,
            """{"detail": "Şu an yoğunluk veya bağlantı sorunu yaşıyoruz, birkaç saniye sonra tekrar dener misin?"}""",
        )

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertTrue(sonuc.isFailure)
        assertTrue(sonuc.exceptionOrNull()?.message.orEmpty().contains("tekrar dener misin"))
    }

    @Test
    fun json_olmayan_hata_govdesinde_durum_kodu_gosterilir() = runTest {
        // Gateway hataları (502 vb.) HTML dönebilir; uygulama çökmeden anlaşılır bir mesaj vermeli.
        val sahte = SahteSunucu {
            respond("<html>Bad Gateway</html>", HttpStatusCode.BadGateway, headersOf(HttpHeaders.ContentType, "text/html"))
        }

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertEquals("Sunucu hatası (502), lütfen daha sonra tekrar dene.", sonuc.exceptionOrNull()?.message)
    }

    @Test
    fun baglanti_hatasi_cokmeden_hata_olarak_doner() = runTest {
        val sahte = SahteSunucu { throw IllegalStateException("Bağlantı kurulamadı") }

        val sonuc = DusApiClient(sahte.engine).askQuestion("Soru", emptyList())

        assertTrue(sonuc.isFailure)
    }
}
