package com.ilhanaltunbas.dusassistant

import com.ilhanaltunbas.dusassistant.core.Platform
import platform.UIKit.UIDevice

class IOSPlatform: Platform {
    override val name: String = UIDevice.currentDevice.systemName() + " " + UIDevice.currentDevice.systemVersion
}

actual fun getPlatform(): Platform = IOSPlatform()