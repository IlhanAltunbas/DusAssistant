package com.ilhanaltunbas.dusassistant.core

interface Platform {
    val name: String
}

expect fun getPlatform(): Platform