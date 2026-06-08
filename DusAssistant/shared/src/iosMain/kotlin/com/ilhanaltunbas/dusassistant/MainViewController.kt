package com.ilhanaltunbas.dusassistant

import androidx.compose.ui.window.ComposeUIViewController
import com.ilhanaltunbas.dusassistant.data.local.getDatabaseBuilder
import com.ilhanaltunbas.dusassistant.data.local.getRoomDatabase
import com.ilhanaltunbas.dusassistant.presentation.App

fun MainViewController() = ComposeUIViewController {
    val database = getRoomDatabase(getDatabaseBuilder())
    App(database)
}
