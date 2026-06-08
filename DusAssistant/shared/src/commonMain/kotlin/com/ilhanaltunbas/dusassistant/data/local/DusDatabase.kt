package com.ilhanaltunbas.dusassistant.data.local

import androidx.room.ConstructedBy
import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.RoomDatabaseConstructor

@Database(entities = [ChatSessionEntity::class, MessageEntity::class], version = 2)
@ConstructedBy(DusDatabaseConstructor::class)
abstract class DusDatabase : RoomDatabase() {
    abstract fun dusDao(): DusDao
}

@Suppress("NO_ACTUAL_FOR_EXPECT")
expect object DusDatabaseConstructor : RoomDatabaseConstructor<DusDatabase>
