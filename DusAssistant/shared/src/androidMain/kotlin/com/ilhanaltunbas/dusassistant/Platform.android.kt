package com.ilhanaltunbas.dusassistant.core

import android.os.Build
import com.ilhanaltunbas.dusassistant.core.Platform

class AndroidPlatform : Platform {
    override val name: String = "Android ${Build.VERSION.SDK_INT}"
}

actual fun getPlatform(): Platform = AndroidPlatform()