// MacAPKApp.swift — Entry point
import SwiftUI

@main
struct MacAPKApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        MenuBarExtra("MacAPK", systemImage: "shield") {
            DashboardView()
        }
        .menuBarExtraStyle(.window)
    }
}