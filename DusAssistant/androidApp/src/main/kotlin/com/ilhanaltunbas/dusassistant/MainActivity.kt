package com.ilhanaltunbas.dusassistant

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import com.ilhanaltunbas.dusassistant.data.local.DusDatabase
import com.ilhanaltunbas.dusassistant.data.local.getDatabaseBuilder
import com.ilhanaltunbas.dusassistant.data.local.getRoomDatabase
import com.ilhanaltunbas.dusassistant.presentation.App

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)

        val database = getRoomDatabase(getDatabaseBuilder(applicationContext))

        setContent {
            App(database)
        }
    }
}

@Preview
@Composable
fun AppAndroidPreview() {
    // App() // Needs DusDatabase instance
}