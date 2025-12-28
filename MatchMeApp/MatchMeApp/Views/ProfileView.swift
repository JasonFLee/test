import SwiftUI

struct ProfileView: View {
    @EnvironmentObject var appState: AppState
    @State private var showingResetAlert: Bool = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Profile header
                    profileHeader

                    // Interview summary
                    interviewSummary

                    // Settings
                    settingsSection

                    Spacer()
                }
                .padding()
            }
            .navigationTitle("Profile")
            .alert("Reset Profile", isPresented: $showingResetAlert) {
                Button("Cancel", role: .cancel) {}
                Button("Reset", role: .destructive) {
                    appState.reset()
                }
            } message: {
                Text("This will delete all your data and you'll need to start over. Are you sure?")
            }
        }
    }

    private var profileHeader: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [.purple, .pink]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 100, height: 100)

                Image(systemName: "person.circle.fill")
                    .font(.system(size: 50))
                    .foregroundColor(.white)
            }

            if let user = appState.currentUser {
                VStack(spacing: 4) {
                    Text("\(user.name), \(user.age)")
                        .font(.title2)
                        .fontWeight(.bold)

                    Text("Interview completed")
                        .font(.caption)
                        .foregroundColor(.green)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 4)
                        .background(Color.green.opacity(0.1))
                        .cornerRadius(12)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(20)
    }

    private var interviewSummary: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Your Interview Responses")
                .font(.headline)

            if let user = appState.currentUser {
                ForEach(appState.questions.indices, id: \.self) { index in
                    let question = appState.questions[index]
                    if let response = user.interviewResponses.first(where: { $0.questionId == question.id }) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(question.category.rawValue)
                                .font(.caption)
                                .foregroundColor(.purple)

                            Text(question.text)
                                .font(.subheadline)
                                .foregroundColor(.secondary)

                            Text(response.answer)
                                .font(.body)
                                .fontWeight(.medium)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(UIColor.tertiarySystemBackground))
                        .cornerRadius(12)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(20)
    }

    private var settingsSection: some View {
        VStack(spacing: 12) {
            Button(action: {
                showingResetAlert = true
            }) {
                HStack {
                    Image(systemName: "arrow.counterclockwise")
                    Text("Retake Interview")
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundColor(.secondary)
                }
                .foregroundColor(.primary)
                .padding()
                .background(Color(UIColor.secondarySystemBackground))
                .cornerRadius(12)
            }

            Button(action: {
                // About action
            }) {
                HStack {
                    Image(systemName: "info.circle")
                    Text("About MatchMe")
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundColor(.secondary)
                }
                .foregroundColor(.primary)
                .padding()
                .background(Color(UIColor.secondarySystemBackground))
                .cornerRadius(12)
            }
        }
    }
}

#Preview {
    ProfileView()
        .environmentObject(AppState())
}
