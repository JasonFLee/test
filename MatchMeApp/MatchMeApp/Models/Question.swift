import Foundation

struct InterviewQuestion: Identifiable {
    let id: UUID
    let text: String
    let category: QuestionCategory
    let type: QuestionType
    let options: [String]?
    let weight: Double

    init(
        id: UUID = UUID(),
        text: String,
        category: QuestionCategory,
        type: QuestionType,
        options: [String]? = nil,
        weight: Double = 1.0
    ) {
        self.id = id
        self.text = text
        self.category = category
        self.type = type
        self.options = options
        self.weight = weight
    }
}

enum QuestionCategory: String, CaseIterable, Codable {
    case personality = "Personality"
    case lifestyle = "Lifestyle"
    case values = "Values"
    case interests = "Interests"
    case relationship = "Relationship Goals"
}

enum QuestionType: String, Codable {
    case multipleChoice
    case scale
    case openEnded
}

// MARK: - Default Interview Questions
extension InterviewQuestion {
    static let defaultQuestions: [InterviewQuestion] = [
        // Personality
        InterviewQuestion(
            text: "How would you describe your ideal weekend?",
            category: .personality,
            type: .multipleChoice,
            options: [
                "Adventure outdoors - hiking, exploring",
                "Cozy at home - movies, books, cooking",
                "Social butterfly - parties, events, friends",
                "Productive - projects, learning, creating"
            ],
            weight: 1.2
        ),
        InterviewQuestion(
            text: "In social situations, you typically...",
            category: .personality,
            type: .multipleChoice,
            options: [
                "Love being the center of attention",
                "Enjoy small group conversations",
                "Prefer one-on-one interactions",
                "Need alone time to recharge after"
            ],
            weight: 1.3
        ),

        // Lifestyle
        InterviewQuestion(
            text: "How important is fitness and health to you?",
            category: .lifestyle,
            type: .multipleChoice,
            options: [
                "It's my lifestyle - daily workouts",
                "Pretty important - regular exercise",
                "Moderate - occasional activity",
                "Not a priority right now"
            ],
            weight: 1.0
        ),
        InterviewQuestion(
            text: "Your approach to planning is...",
            category: .lifestyle,
            type: .multipleChoice,
            options: [
                "Spontaneous - go with the flow",
                "Flexible - rough plans, open to change",
                "Balanced - some structure, some freedom",
                "Organized - detailed plans and schedules"
            ],
            weight: 1.1
        ),

        // Values
        InterviewQuestion(
            text: "What matters most to you in life?",
            category: .values,
            type: .multipleChoice,
            options: [
                "Career and achievement",
                "Family and relationships",
                "Personal growth and learning",
                "Experiences and adventure"
            ],
            weight: 1.5
        ),
        InterviewQuestion(
            text: "How do you handle disagreements?",
            category: .values,
            type: .multipleChoice,
            options: [
                "Address it immediately and directly",
                "Take time to think, then discuss calmly",
                "Avoid conflict when possible",
                "Seek compromise and middle ground"
            ],
            weight: 1.4
        ),

        // Interests
        InterviewQuestion(
            text: "Pick your ideal date activity:",
            category: .interests,
            type: .multipleChoice,
            options: [
                "Trying a new restaurant",
                "Outdoor adventure or sports",
                "Concert, museum, or cultural event",
                "Cooking together at home"
            ],
            weight: 1.0
        ),
        InterviewQuestion(
            text: "What kind of content do you consume most?",
            category: .interests,
            type: .multipleChoice,
            options: [
                "Podcasts and audiobooks",
                "TV shows and movies",
                "Social media and videos",
                "Books and articles"
            ],
            weight: 0.8
        ),

        // Relationship Goals
        InterviewQuestion(
            text: "What are you looking for?",
            category: .relationship,
            type: .multipleChoice,
            options: [
                "Something serious and long-term",
                "Open to seeing where things go",
                "Casual dating and fun",
                "New friends, maybe more"
            ],
            weight: 2.0
        ),
        InterviewQuestion(
            text: "Your ideal communication style in a relationship:",
            category: .relationship,
            type: .multipleChoice,
            options: [
                "Constant texting throughout the day",
                "A few check-ins, quality conversations",
                "Mainly when we're together in person",
                "Flexible - depends on the day"
            ],
            weight: 1.3
        )
    ]
}
