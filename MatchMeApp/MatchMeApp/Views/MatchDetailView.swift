import SwiftUI

struct MatchDetailView: View {
    let match: Match
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Profile header
                    profileHeader

                    // Compatibility section
                    compatibilitySection

                    // Commonalities
                    if !match.commonalities.isEmpty {
                        commonalitiesSection
                    }

                    // Action buttons
                    actionButtons

                    Spacer()
                }
                .padding()
            }
            .navigationTitle("Match Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
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
                    .frame(width: 120, height: 120)

                Image(systemName: match.user.profileImageName)
                    .font(.system(size: 60))
                    .foregroundColor(.white)
            }

            VStack(spacing: 4) {
                Text("\(match.user.name), \(match.user.age)")
                    .font(.title)
                    .fontWeight(.bold)

                Text(match.user.bio)
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
        }
    }

    private var compatibilitySection: some View {
        VStack(spacing: 12) {
            Text("Compatibility Score")
                .font(.headline)

            ZStack {
                Circle()
                    .stroke(Color.gray.opacity(0.2), lineWidth: 12)
                    .frame(width: 150, height: 150)

                Circle()
                    .trim(from: 0, to: CGFloat(match.compatibilityPercentage) / 100)
                    .stroke(
                        LinearGradient(
                            gradient: Gradient(colors: [.purple, .pink]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        style: StrokeStyle(lineWidth: 12, lineCap: .round)
                    )
                    .frame(width: 150, height: 150)
                    .rotationEffect(.degrees(-90))

                VStack {
                    Text("\(match.compatibilityPercentage)%")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text(match.compatibilityLabel)
                        .font(.caption)
                        .foregroundColor(.purple)
                }
            }
        }
        .padding()
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(20)
    }

    private var commonalitiesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("What you have in common")
                .font(.headline)

            VStack(alignment: .leading, spacing: 8) {
                ForEach(match.commonalities, id: \.self) { trait in
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)

                        Text(trait)
                            .font(.body)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(20)
    }

    private var actionButtons: some View {
        VStack(spacing: 12) {
            Button(action: {
                // Start chat action
            }) {
                HStack {
                    Image(systemName: "message.fill")
                    Text("Start Conversation")
                }
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding()
                .background(
                    LinearGradient(
                        gradient: Gradient(colors: [.purple, .pink]),
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .cornerRadius(16)
            }

            Button(action: {
                // Skip action
            }) {
                Text("Not Interested")
                    .font(.headline)
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    MatchDetailView(match: Match(
        user: User(name: "Test User", age: 25, bio: "Hello!", isInterviewComplete: true),
        compatibilityScore: 0.85,
        commonalities: ["Similar personality", "Same goals"]
    ))
}
