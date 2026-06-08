package com.ilhanaltunbas.dusassistant.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForwardIos
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ilhanaltunbas.dusassistant.data.local.DusDatabase
import com.ilhanaltunbas.dusassistant.data.remote.DusApiClient
import com.ilhanaltunbas.dusassistant.data.repository.DusRepository
import kotlinx.coroutines.launch

// Modern Koyu/Gri Renk Paleti
val AppBackgroundColor = Color(0xFF0F0F0F)
val SurfaceColor = Color(0xFF1A1A1A) 
val UserBubbleColor = Color(0xFF252525)
val AssistantBubbleColor = Color(0xFF1E1E1E)
val TextPrimary = Color.White
val TextSecondary = Color(0xFF9E9E9E)

@Composable
fun App(database: DusDatabase) {
    val darkColors = darkColorScheme(
        primary = Color.White,
        onPrimary = AppBackgroundColor,
        secondary = TextSecondary,
        onSecondary = Color.White,
        background = AppBackgroundColor,
        surface = SurfaceColor,
        onSurface = Color.White
    )

    MaterialTheme(colorScheme = darkColors) {
        val apiClient = remember { DusApiClient() }
        val repository = remember(database) { DusRepository(apiClient, database.dusDao()) }
        val viewModel = remember(repository) { DusChatViewModel(repository) }

        MainNavigationWrapper(viewModel)
    }
}

@Composable
fun MainNavigationWrapper(viewModel: DusChatViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                modifier = Modifier.width(280.dp),
                drawerContainerColor = SurfaceColor,
                drawerShape = RoundedCornerShape(topEnd = 12.dp, bottomEnd = 12.dp)
            ) {
                Spacer(Modifier.height(32.dp))
                Text(
                    "DusAssistant",
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color.White
                )
                NavigationDrawerItem(
                    label = { Text("Yeni Sohbet", fontWeight = FontWeight.Medium) },
                    selected = false,
                    onClick = { 
                        viewModel.createNewChat()
                        scope.launch { drawerState.close() }
                    },
                    icon = { Icon(Icons.Default.Add, contentDescription = null) },
                    modifier = Modifier.padding(horizontal = 12.dp),
                    colors = NavigationDrawerItemDefaults.colors(
                        unselectedContainerColor = Color.Transparent,
                        unselectedIconColor = TextSecondary,
                        unselectedTextColor = TextSecondary
                    )
                )
                HorizontalDivider(modifier = Modifier.padding(20.dp), color = UserBubbleColor, thickness = 0.5.dp)
                
                Text(
                    "GEÇMİŞ SOHBETLER",
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                
                LazyColumn(
                    modifier = Modifier.fillWeight(),
                    contentPadding = PaddingValues(horizontal = 12.dp)
                ) {
                    items(uiState.sessions) { session ->
                        NavigationDrawerItem(
                            label = { 
                                Text(
                                    session.title, 
                                    maxLines = 1,
                                    modifier = Modifier.fillMaxWidth()
                                ) 
                            },
                            selected = uiState.currentSessionId == session.id,
                            onClick = { 
                                viewModel.selectSession(session.id)
                                scope.launch { drawerState.close() }
                            },
                            icon = { Icon(Icons.Default.ChatBubbleOutline, contentDescription = null, modifier = Modifier.size(18.dp)) },
                            badge = {
                                IconButton(
                                    onClick = { viewModel.deleteSession(session.id) },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        Icons.Default.DeleteOutline, 
                                        contentDescription = "Sil",
                                        tint = TextSecondary.copy(alpha = 0.6f),
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                            },
                            colors = NavigationDrawerItemDefaults.colors(
                                selectedContainerColor = UserBubbleColor,
                                unselectedContainerColor = Color.Transparent,
                                selectedTextColor = Color.White,
                                unselectedTextColor = TextSecondary,
                                selectedIconColor = Color.White,
                                unselectedIconColor = TextSecondary
                            )
                        )
                    }
                }
            }
        }
    ) {
        ChatScreen(
            viewModel = viewModel,
            onMenuClick = { scope.launch { drawerState.open() } }
        )
    }
}

// Helper extension to make the drawer list take available space
@Composable
private fun Modifier.fillWeight() = this.fillMaxHeight().padding(bottom = 16.dp)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(viewModel: DusChatViewModel, onMenuClick: () -> Unit) {
    val uiState by viewModel.uiState.collectAsState()
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val focusManager = LocalFocusManager.current

    LaunchedEffect(uiState.messages.size) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "DusAssistant",
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Default.Menu, contentDescription = "Menü", tint = TextPrimary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = AppBackgroundColor
                )
            )
        },
        contentWindowInsets = WindowInsets(0, 0, 0, 0) // Scaffold'un otomatik insetlerini sıfırladık
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = paddingValues.calculateTopPadding()) // Sadece TopAppBar için üstten boşluk
                .background(AppBackgroundColor)
        ) {
            // Mesaj Listesi - Artık ekranın kalan tüm yerini kaplar ve barı aşağı iter
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(uiState.messages) { message ->
                    MessageBubble(message)
                }

                if (uiState.isLoading) {
                    item {
                        AssistantTypingIndicator()
                    }
                }

                // Barın altında kalmaması için sona boşluk
                item {
                    Spacer(Modifier.height(100.dp))
                }
            }

            uiState.errorMessage?.let { error ->
                Text(
                    text = error,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                        .background(Color.Black.copy(alpha = 0.6f), RoundedCornerShape(8.dp))
                        .padding(8.dp),
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }

            // Chat Bar - Artık listenin altında, onu yukarı itecek şekilde konumlandı
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .imePadding() // Klavye geldiğinde bu kutu ve üstündeki liste yükselir
                    .padding(bottom = 24.dp) // Biraz daha yukarı alındı (12 -> 24)
            ) {
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 56.dp)
                        .border(
                            width = 1.dp,
                            brush = Brush.verticalGradient(
                                colors = listOf(
                                    Color.White.copy(alpha = 0.25f),
                                    Color.White.copy(alpha = 0.08f)
                                )
                            ),
                            shape = RoundedCornerShape(28.dp)
                        )
                        .clip(RoundedCornerShape(28.dp)),
                    color = SurfaceColor.copy(alpha = 0.95f), // Opaklık arttırıldı
                    tonalElevation = 0.dp
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 20.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        TextField(
                            value = inputText,
                            onValueChange = { inputText = it },
                            modifier = Modifier.weight(1f),
                            placeholder = { Text("Düşüncelerini sor...", fontSize = 15.sp, color = TextSecondary) },
                            colors = TextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedContainerColor = Color.Transparent,
                                unfocusedContainerColor = Color.Transparent,
                                disabledContainerColor = Color.Transparent,
                                focusedIndicatorColor = Color.Transparent,
                                unfocusedIndicatorColor = Color.Transparent,
                                cursorColor = Color.White
                            ),
                            maxLines = 4
                        )

                        IconButton(
                            onClick = {
                                if (inputText.isNotBlank()) {
                                    viewModel.sendMessage(inputText)
                                    inputText = ""
                                    focusManager.clearFocus()
                                }
                            },
                            enabled = inputText.isNotBlank() && !uiState.isLoading
                        ) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.ArrowForwardIos,
                                contentDescription = "Gönder",
                                tint = if (inputText.isNotBlank()) Color.White else Color.White.copy(alpha = 0.3f),
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MessageBubble(message: ChatMessage) {
    val isUser = message.isUser
    val alignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart
    val bubbleShape = RoundedCornerShape(12.dp)
    val bubbleColor = if (isUser) UserBubbleColor else AssistantBubbleColor
    
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = alignment
    ) {
        Surface(
            color = bubbleColor,
            shape = bubbleShape,
            modifier = Modifier.widthIn(max = 280.dp)
        ) {
            Text(
                text = message.text,
                modifier = Modifier.padding(14.dp),
                color = Color.White,
                style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 22.sp)
            )
        }
    }
}

@Composable
fun AssistantTypingIndicator() {
    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
        Surface(
            color = AssistantBubbleColor,
            shape = RoundedCornerShape(12.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(12.dp),
                    strokeWidth = 2.dp,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Cevap hazırlanıyor", fontSize = 13.sp, color = TextSecondary)
            }
        }
    }
}
