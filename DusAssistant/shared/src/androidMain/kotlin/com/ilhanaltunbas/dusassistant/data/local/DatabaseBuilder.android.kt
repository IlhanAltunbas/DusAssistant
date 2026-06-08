package com.ilhanaltunbas.dusassistant.data.local

import android.content.Context
import androidx.room.Room
import androidx.room.RoomDatabase

fun getDatabaseBuilder(context: Context): RoomDatabase.Builder<DusDatabase> {
    val dbFile = context.getDatabasePath("dus_chat.db")
    return Room.databaseBuilder<DusDatabase>(
        context = context.applicationContext,
        name = dbFile.absolutePath
    )
}