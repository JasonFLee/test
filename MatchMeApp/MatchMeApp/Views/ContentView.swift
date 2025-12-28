import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            if !appState.isOnboarded {
                OnboardingView()
            } else if !appState.hasCompletedInterview {
                InterviewView()
            } else {
                MainTabView()
            }
        }
        .animation(.easeInOut, value: appState.isOnboarded)
        .animation(.easeInOut, value: appState.hasCompletedInterview)
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
