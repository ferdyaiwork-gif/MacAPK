import SwiftUI
import UserNotifications

// MARK: - App Entry Point

@main
struct MacAPKApp: App {
    @StateObject private var appState = AppState()
    
    var body: some Scene {
        MenuBarExtra("MacAPK", systemImage: "shield.checkered") {
            DashboardView(appState: appState)
        }
        .menuBarExtraStyle(.window)
    }
}

// MARK: - App State

class AppState: ObservableObject {
    @Published var score: Int = 0
    @Published var status: String = "grijs"
    @Published var modules: [ModuleInfo] = []
    @Published var isLoading: Bool = false
    @Published var lastUpdate: String = "Nooit"
    @Published var serverRunning: Bool = false
    
    private var serverProcess: Process?
    private var refreshTimer: Timer?
    let serverPort: Int = 8899
    
    init() {
        // Wait a bit before starting, to let UI load
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            self.startServer()
            self.runCheck()
            self.startAutoRefresh()
        }
    }
    
    deinit {
        serverProcess?.terminate()
        refreshTimer?.invalidate()
    }
    
    func startServer() {
        let resourcePath = Bundle.main.resourcePath ?? ""
        let scriptCandidates = [
            "\(resourcePath)/backend/macapk",
            "\(resourcePath)/backend/macapk_server",
            "/Users/ferdy/projects/MacAPK/macapk"
        ]
        
        // Check if server already running
        guard !isServerRunning() else {
            serverRunning = true
            return
        }
        
        let scriptPath = scriptCandidates.first { FileManager.default.fileExists(atPath: $0) } ?? scriptCandidates.last!
        let pythonPath = ["/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3", "/usr/bin/python3", "/usr/local/bin/python3"]
            .first { FileManager.default.fileExists(atPath: $0) } ?? "/usr/bin/python3"
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = [scriptPath, "--port", "\(serverPort)"]
        
        var env = ProcessInfo.processInfo.environment
        env["MACAPK_UI_DIR"] = "\(resourcePath)/ui"
        process.environment = env
        
        do {
            try process.run()
            self.serverProcess = process
            self.serverRunning = true
            print("MacAPK: Server started on port \(serverPort)")
        } catch {
            print("MacAPK: Failed to start server: \(error)")
            // Try connecting to existing server
            self.serverRunning = isServerRunning()
        }
    }
    
    func isServerRunning() -> Bool {
        guard let url = URL(string: "http://127.0.0.1:\(serverPort)/api/status") else { return false }
        let semaphore = DispatchSemaphore(value: 0)
        var running = false
        
        URLSession.shared.dataTask(with: url) { data, response, _ in
            running = (response as? HTTPURLResponse)?.statusCode == 200
            semaphore.signal()
        }.resume()
        _ = semaphore.wait(timeout: .now() + 3)
        return running
    }
    
    func runCheck() {
        guard !isLoading else { return }
        isLoading = true
        
        guard let url = URL(string: "http://127.0.0.1:\(serverPort)/api/check") else {
            isLoading = false
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60
        
        URLSession.shared.dataTask(with: request) { data, _, _ in
            DispatchQueue.main.async {
                self.isLoading = false
                guard let data = data else { return }
                
                do {
                    let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
                    let scores = json["scores"] as? [String: Any] ?? [:]
                    
                    self.score = scores["overall"] as? Int ?? 0
                    self.status = scores["overall_status"] as? String ?? "onbekend"
                    
                    var newModules: [ModuleInfo] = []
                    if let modulesDict = scores["modules"] as? [String: [String: Any]] {
                        let order = ["cpu", "gpu", "ram", "disk", "battery", "network", "sensors", "security", "processes"]
                        for key in order {
                            if let value = modulesDict[key] {
                                newModules.append(ModuleInfo(
                                    id: key,
                                    name: self.displayName(key),
                                    score: value["score"] as? Int ?? 0,
                                    status: value["status"] as? String ?? "onbekend",
                                    diagnoses: value["diagnoses"] as? [String] ?? []
                                ))
                            }
                        }
                    }
                    self.modules = newModules
                    self.lastUpdate = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .short)
                    self.serverRunning = true
                    
                    // Send notification for low scores
                    self.checkNotifications()
                } catch {
                    print("Parse error: \(error)")
                }
            }
        }.resume()
    }
    
    func startAutoRefresh() {
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { _ in
            self.runCheck()
        }
    }
    
    func checkNotifications() {
        if status == "rood" || (status == "geel" && score < 50) {
            let content = UNMutableNotificationContent()
            content.title = status == "rood" ? "MacAPK — Kritiek!" : "MacAPK — Waarschuwing"
            content.body = "Systeem score: \(score)/100"
            content.sound = .default
            
            let request = UNNotificationRequest(identifier: "macapk-score", content: content, trigger: nil)
            UNUserNotificationCenter.current().add(request)
        }
    }
    
    func displayName(_ key: String) -> String {
        switch key {
        case "cpu": return "Motor (CPU)"
        case "gpu": return "Grafisch (GPU)"
        case "ram": return "Geheugen"
        case "disk": return "Opslag"
        case "battery": return "Accu"
        case "network": return "Netwerk"
        case "sensors": return "Temperatuur"
        case "security": return "Veiligheid"
        case "processes": return "Processen"
        default: return key.capitalized
        }
    }
    
    func openInBrowser() {
        if let url = URL(string: "http://127.0.0.1:\(serverPort)") {
            NSWorkspace.shared.open(url)
        }
    }
    
    func quit() {
        serverProcess?.terminate()
        NSApp.terminate(nil)
    }
}

// MARK: - Module Info

struct ModuleInfo: Identifiable {
    let id: String
    let name: String
    let score: Int
    let status: String
    let diagnoses: [String]
}