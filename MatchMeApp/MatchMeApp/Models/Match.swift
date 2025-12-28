import Foundation

struct Match: Identifiable {
    let id: UUID
    let user: User
    let compatibilityScore: Double
    let matchedAt: Date
    let commonalities: [String]

    init(
        id: UUID = UUID(),
        user: User,
        compatibilityScore: Double,
        matchedAt: Date = Date(),
        commonalities: [String] = []
    ) {
        self.id = id
        self.user = user
        self.compatibilityScore = compatibilityScore
        self.matchedAt = matchedAt
        self.commonalities = commonalities
    }

    var compatibilityPercentage: Int {
        Int(compatibilityScore * 100)
    }

    var compatibilityLabel: String {
        switch compatibilityScore {
        case 0.9...1.0:
            return "Perfect Match"
        case 0.75..<0.9:
            return "Great Match"
        case 0.6..<0.75:
            return "Good Match"
        case 0.45..<0.6:
            return "Potential Match"
        default:
            return "New Connection"
        }
    }
}
