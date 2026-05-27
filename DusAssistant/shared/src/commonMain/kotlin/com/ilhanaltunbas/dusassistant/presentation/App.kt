package com.ilhanaltunbas.dusassistant.presentation

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.safeContentPadding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import org.jetbrains.compose.resources.painterResource

import dusassistant.shared.generated.resources.Res
import dusassistant.shared.generated.resources.compose_multiplatform

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.ilhanaltunbas.dusassistant.data.remote.DusApiClient
import com.ilhanaltunbas.dusassistant.data.repository.DusRepository

@Composable
fun App() {
    MaterialTheme {
        // Basit Dependency Injection: Sınıfları sırasıyla ayağa kaldırıp birbirine bağlıyoruz
        val apiClient = remember { DusApiClient() }
        val repository = remember { DusRepository(apiClient) }
        val viewModel = remember { DusChatViewModel(repository) }

        // Ana ekranımızı çağırıyoruz
        ChatScreen(viewModel = viewModel)
    }
}

@Composable
fun ChatScreen(viewModel: DusChatViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    var inputText by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F5F5))
    ) {
        // Üst Kısım: Mesaj Listesi
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            contentPadding = PaddingValues(vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(uiState.messages) { message ->
                MessageBubble(message)
            }
        }

        // Yükleniyor Animasyonu (Ortada Dönen İkon)
        if (uiState.isLoading) {
            CircularProgressIndicator(
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(8.dp)
            )
        }

        // Hata Mesajı
        uiState.errorMessage?.let { error ->
            Text(
                text = error,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(8.dp)
            )
        }

        // Alt Kısım: Soru Yazma Alanı
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White)
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("DUS Asistanına bir soru sor...") },
                maxLines = 3
            )
            Spacer(modifier = Modifier.width(8.dp))
            Button(
                onClick = {
                    viewModel.sendMessage(inputText)
                    inputText = "" // Gönderdikten sonra kutuyu temizle
                },
                enabled = inputText.isNotBlank() && !uiState.isLoading
            ) {
                Text("Gönder")
            }
        }
    }
}

// Mesaj Balonu Tasarımı
@Composable
fun MessageBubble(message: ChatMessage) {
    // Kullanıcı mesajları sağa, asistan mesajları sola hizalanır
    val alignment = if (message.isUser) Alignment.CenterEnd else Alignment.CenterStart
    val backgroundColor = if (message.isUser) Color(0xFFE3F2FD) else Color.White

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = alignment
    ) {
        Surface(
            shape = RoundedCornerShape(12.dp),
            color = backgroundColor,
            shadowElevation = 1.dp,
            modifier = Modifier.widthIn(max = 300.dp)
        ) {
            Text(
                text = message.text,
                modifier = Modifier.padding(12.dp),
                color = Color.Black
            )
        }
    }
}