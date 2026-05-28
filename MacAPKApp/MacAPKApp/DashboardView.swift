import SwiftUI

struct DashboardView: View {
    @ObservedObject var appState: AppState
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            headerBar
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            
            Divider()
            
            // Score Circle
            scoreSection
                .padding(.vertical, 10)
            
            Divider()
            
            // Module Grid
            ScrollView {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 6) {
                    ForEach(appState.modules) { module in
                        ModuleCard(module: module)
                    }
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 8)
            }
            
            Divider()
            
            // Actions
            actionBar
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
        }
        .frame(width: 360, height: 520)
    }
    
    // MARK: - Header
    
    var headerBar: some View {
        HStack {
            Image(systemName: statusIcon)
                .font(.title3)
                .foregroundColor(statusColor)
            Text("MacAPK")
                .font(.headline)
            if appState.isLoading {
                Spacer()
                ProgressView()
                    .scaleEffect(0.7)
            }
            Spacer()
            Text(appState.lastUpdate)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
    }
    
    // MARK: - Score
    
    var scoreSection: some View {
        VStack(spacing: 4) {
            ZStack {
                Circle()
                    .stroke(Color.gray.opacity(0.2), lineWidth: 8)
                    .frame(width: 90, height: 90)
                Circle()
                    .trim(from: 0, to: max(CGFloat(appState.score) / 100, 0.01))
                    .stroke(statusColor, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                    .frame(width: 90, height: 90)
                    .rotationEffect(.degrees(-90))
                    .animation(.easeInOut(duration: 0.8), value: appState.score)
                VStack(spacing: 0) {
                    Text("\(appState.score)")
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                    Text("van 100")
                        .font(.system(size: 9))
                        .foregroundColor(.secondary)
                }
            }
            Text(statusText)
                .font(.subheadline.bold())
                .foregroundColor(statusColor)
        }
    }
    
    // MARK: - Actions
    
    var actionBar: some View {
        HStack {
            Button {
                appState.runCheck()
            } label: {
                Label("Keuring", systemImage: "magnifyingglass")
                    .font(.caption)
            }
            .buttonStyle(.borderedProminent)
            .disabled(appState.isLoading)
            
            Spacer()
            
            Button {
                appState.openInBrowser()
            } label: {
                Label("Browser", systemImage: "safari")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
            
            Button {
                appState.quit()
            } label: {
                Label("Stop", systemImage: "xmark")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
        }
    }
    
    // MARK: - Style helpers
    
    var statusIcon: String {
        switch appState.status {
        case "groen": return "checkmark.shield.fill"
        case "geel": return "exclamationmark.shield.fill"
        case "rood": return "xmark.shield.fill"
        default: return "shield"
        }
    }
    
    var statusColor: Color {
        switch appState.status {
        case "groen": return .green
        case "geel": return .yellow
        case "rood": return .red
        default: return .gray
        }
    }
    
    var statusText: String {
        switch appState.status {
        case "groen": return "Goedgekeurd ✅"
        case "geel": return "Waarschuwing ⚠️"
        case "rood": return "Kritiek 🚨"
        default: return "Laden..."
        }
    }
}

// MARK: - Module Card

struct ModuleCard: View {
    let module: ModuleInfo
    
    var moduleColor: Color {
        switch module.status {
        case "groen": return .green
        case "geel": return .yellow
        case "rood": return .red
        default: return .gray
        }
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack {
                Circle()
                    .fill(moduleColor)
                    .frame(width: 7, height: 7)
                Text(module.name)
                    .font(.caption.bold())
                    .lineLimit(1)
                Spacer()
                Text("\(module.score)")
                    .font(.caption.bold())
                    .foregroundColor(moduleColor)
            }
            if let diag = module.diagnoses.first {
                Text(diag)
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(6)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color(nsColor: .controlBackgroundColor)))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(moduleColor.opacity(0.3), lineWidth: 1))
    }
}

#Preview {
    DashboardView(appState: AppState())
}