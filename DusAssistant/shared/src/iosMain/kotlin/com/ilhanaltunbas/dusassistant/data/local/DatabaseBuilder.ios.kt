package com.ilhanaltunbas.dusassistant.data.local

import androidx.room.Room
import androidx.room.RoomDatabase
import platform.Foundation.NSHomeDirectory

fun getDatabaseBuilder(): RoomDatabase.Builder<DusDatabase> {
    val dbFilePath = NSHomeDirectory() + "/dus_chat.db"
    return Room.databaseBuilder<DusDatabase>(
        name = dbFilePath
    )
}