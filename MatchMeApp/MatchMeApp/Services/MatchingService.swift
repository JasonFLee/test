import Foundation

class MatchingService {
    private let questions: [InterviewQuestion]

    init(questions: [InterviewQuestion] = InterviewQuestion.defaultQuestions) {
        self.questions = questions
    }

    /// Calculate compatibility score between two users based on their interview responses
    func calculateCompatibility(user1: User, user2: User) -> Double {
        guard user1.isInterviewComplete && user2.isInterviewComplete else {
            return 0.0
        }

        var totalWeight: Double = 0
        var weightedScore: Double = 0

        for question in questions {
            guard let response1 = user1.interviewResponses.first(where: { $0.questionId == question.id }),
                  let response2 = user2.interviewResponses.first(where: { $0.questionId == question.id }) else {
                continue
            }

            let similarity = calculateResponseSimilarity(
                response1: response1,
                response2: response2,
                question: question
            )

            weightedScore += similarity * question.weight
            totalWeight += question.weight
        }

        guard totalWeight > 0 else { return 0.0 }

        return weightedScore / totalWeight
    }

    /// Calculate similarity between two responses
    private func calculateResponseSimilarity(
        response1: InterviewResponse,
        response2: InterviewResponse,
        question: InterviewQuestion
    ) -> Double {
        switch question.type {
        case .multipleChoice:
            return calculateMultipleChoiceSimilarity(response1: response1, response2: response2, question: question)
        case .scale:
            return calculateScaleSimilarity(response1: response1, response2: response2)
        case .openEnded:
            return calculateOpenEndedSimilarity(response1: response1, response2: response2)
        }
    }

    /// For multiple choice, we use a compatibility matrix approach
    private func calculateMultipleChoiceSimilarity(
        response1: InterviewResponse,
        response2: InterviewResponse,
        question: InterviewQuestion
    ) -> Double {
        guard let index1 = response1.selectedOptionIndex,
              let index2 = response2.selectedOptionIndex,
              let options = question.options else {
            return 0.0
        }

        // Exact match = 1.0
        if index1 == index2 {
            return 1.0
        }

        // Adjacent options = 0.7 (close compatibility)
        if abs(index1 - index2) == 1 {
            return 0.7
        }

        // Two apart = 0.4
        if abs(index1 - index2) == 2 {
            return 0.4
        }

        // Opposite ends = 0.1
        return 0.1
    }

    /// For scale questions (1-10), closer values = higher compatibility
    private func calculateScaleSimilarity(response1: InterviewResponse, response2: InterviewResponse) -> Double {
        guard let value1 = Int(response1.answer),
              let value2 = Int(response2.answer) else {
            return 0.5
        }

        let maxDiff: Double = 9.0 // Max difference for 1-10 scale
        let actualDiff = Double(abs(value1 - value2))

        return 1.0 - (actualDiff / maxDiff)
    }

    /// For open-ended questions, do basic keyword matching (simplified)
    private func calculateOpenEndedSimilarity(response1: InterviewResponse, response2: InterviewResponse) -> Double {
        let words1 = Set(response1.answer.lowercased().split(separator: " ").map { String($0) })
        let words2 = Set(response2.answer.lowercased().split(separator: " ").map { String($0) })

        guard !words1.isEmpty && !words2.isEmpty else { return 0.5 }

        let commonWords = words1.intersection(words2)
        let totalUniqueWords = words1.union(words2)

        return Double(commonWords.count) / Double(totalUniqueWords.count)
    }

    /// Find common traits between two users based on matching answers
    func findCommonalities(user1: User, user2: User) -> [String] {
        var commonalities: [String] = []

        for question in questions {
            guard let response1 = user1.interviewResponses.first(where: { $0.questionId == question.id }),
                  let response2 = user2.interviewResponses.first(where: { $0.questionId == question.id }),
                  let index1 = response1.selectedOptionIndex,
                  let index2 = response2.selectedOptionIndex,
                  index1 == index2,
                  let options = question.options else {
                continue
            }

            let sharedTrait = generateCommonalityDescription(
                category: question.category,
                option: options[index1]
            )
            commonalities.append(sharedTrait)
        }

        return commonalities
    }

    private func generateCommonalityDescription(category: QuestionCategory, option: String) -> String {
        switch category {
        case .personality:
            return "Similar personality: \(option)"
        case .lifestyle:
            return "Lifestyle match: \(option)"
        case .values:
            return "Shared values"
        case .interests:
            return "Common interest: \(option)"
        case .relationship:
            return "Same relationship goals"
        }
    }

    /// Generate matches for a user from a pool of potential matches
    func generateMatches(for user: User, from potentialMatches: [User], minimumScore: Double = 0.3) -> [Match] {
        var matches: [Match] = []

        for potentialMatch in potentialMatches {
            guard potentialMatch.id != user.id else { continue }
            guard potentialMatch.isInterviewComplete else { continue }

            let score = calculateCompatibility(user1: user, user2: potentialMatch)

            if score >= minimumScore {
                let commonalities = findCommonalities(user1: user, user2: potentialMatch)
                let match = Match(
                    user: potentialMatch,
                    compatibilityScore: score,
                    commonalities: commonalities
                )
                matches.append(match)
            }
        }

        // Sort by compatibility score (highest first)
        return matches.sorted { $0.compatibilityScore > $1.compatibilityScore }
    }
}
