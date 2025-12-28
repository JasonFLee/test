import SwiftUI

struct MatchesView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedMatch: Match? = nil

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Header stats
                    matchStatsHeader

                    if appState.matches.isEmpty {
                        emptyStateView
                    } else {
                        // Match cards
                        LazyVStack(spacing: 16) {
                            ForEach(appState.matches) { match in
                                MatchCard(match: match)
                                    .onTapGesture {
                                        selectedMatch = match
                                    }
                            }
                        }
                        .padding(.horizontal)
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Your Matches")
            .sheet(item: $selectedMatch) { match in
                MatchDetailView(match: match)
            }
        }
    }

    private var matchStatsHeader: some View {
        HStack(spacing: 20) {
            StatCard(
                value: "\(appState.matches.count)",
                label: "Matches",
                icon: "heart.fill",
                color: .pink
            )

            StatCard(
                value: "\(appState.matches.filter { $0.compatibilityScore >= 0.75 }.count)",
                label: "Great Matches",
                icon: "star.fill",
                color: .purple
            )
        }
        .padding(.horizontal)
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "heart.slash")
                .font(.system(size: 60))
                .foregroundColor(.gray)

            Text("No matches yet")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Complete your interview to find compatible matches")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .padding(.top, 60)
    }
}

struct StatCard: View {
    let value: String
    let label: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                Text(value)
                    .font(.title)
                    .fontWeight(.bold)
            }

            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(16)
    }
}

struct MatchCard: View {
    let match: Match

    var body: some View {
        VStack(spacing: 0) {
            // Profile header
            HStack(spacing: 16) {
                // Avatar
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                gradient: Gradient(colors: [.purple, .pink]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 70, height: 70)

                    Image(systemName: match.user.profileImageName)
                        .font(.system(size: 35))
                        .foregroundColor(.white)
                }

                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(match.user.name)
                            .font(.title3)
                            .fontWeight(.semibold)

                        Text("\(match.user.age)")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    Text(match.compatibilityLabel)
                        .font(.caption)
                        .foregroundColor(.purple)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.purple.opacity(0.1))
                        .cornerRadius(8)
                }

                Spacer()

                // Compatibility score
                CompatibilityRing(percentage: match.compatibilityPercentage)
            }
            .padding()

            // Commonalities
            if !match.commonalities.isEmpty {
                Divider()
                    .padding(.horizontal)

                VStack(alignment: .leading, spacing: 8) {
                    Text("You both share:")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    FlowLayout(spacing: 8) {
                        ForEach(match.commonalities.prefix(3), id: \.self) { trait in
                            Text(trait)
                                .font(.caption2)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 6)
                                .background(Color.purple.opacity(0.1))
                                .foregroundColor(.purple)
                                .cornerRadius(12)
                        }
                    }
                }
                .padding()
            }
        }
        .background(Color(UIColor.secondarySystemBackground))
        .cornerRadius(20)
        .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 5)
    }
}

struct CompatibilityRing: View {
    let percentage: Int

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.gray.opacity(0.2), lineWidth: 4)
                .frame(width: 50, height: 50)

            Circle()
                .trim(from: 0, to: CGFloat(percentage) / 100)
                .stroke(
                    LinearGradient(
                        gradient: Gradient(colors: [.purple, .pink]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    style: StrokeStyle(lineWidth: 4, lineCap: .round)
                )
                .frame(width: 50, height: 50)
                .rotationEffect(.degrees(-90))

            Text("\(percentage)%")
                .font(.caption)
                .fontWeight(.bold)
        }
    }
}

// Simple flow layout for tags
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(in: proposal.width ?? 0, subviews: subviews, spacing: spacing)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, subviews: subviews, spacing: spacing)
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.positions[index].x,
                                       y: bounds.minY + result.positions[index].y),
                         proposal: .unspecified)
        }
    }

    struct FlowResult {
        var size: CGSize = .zero
        var positions: [CGPoint] = []

        init(in width: CGFloat, subviews: Subviews, spacing: CGFloat) {
            var x: CGFloat = 0
            var y: CGFloat = 0
            var rowHeight: CGFloat = 0

            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)

                if x + size.width > width && x > 0 {
                    x = 0
                    y += rowHeight + spacing
                    rowHeight = 0
                }

                positions.append(CGPoint(x: x, y: y))
                rowHeight = max(rowHeight, size.height)
                x += size.width + spacing
            }

            self.size = CGSize(width: width, height: y + rowHeight)
        }
    }
}

#Preview {
    MatchesView()
        .environmentObject(AppState())
}
