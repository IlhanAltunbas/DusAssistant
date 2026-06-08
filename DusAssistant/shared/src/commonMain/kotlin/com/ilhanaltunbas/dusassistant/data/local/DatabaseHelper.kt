package com.ilhanaltunbas.dusassistant.data.local

import androidx.room.RoomDatabase
import androidx.sqlite.driver.bundled.BundledSQLiteDriver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO

fun getRoomDatabase(builder: RoomDatabase.Builder<DusDatabase>): DusDatabase {
    return builder
        .setDriver(BundledSQLiteDriver()) // KMP SQLite Sürücüsü
        .setQueryCoroutineContext(Dispatchers.IO) // İşlemleri arka plana at
        .build()
}