import SwiftUI
import UserNotifications

// MARK: - AppDelegate — manages Python backend lifecycle

class AppDelegate: NSObject, NSApplicationDelegate {
    private var serverProcess: Process?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Request notification permissions
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, error in
            if let error = error {
                print("MacAPK: Notification auth error: \(error)")
            }
        }
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        serverProcess?.terminate()
    }
}