import Foundation

struct User: Identifiable, Codable {
    let id: UUID
    var name: String
    var age: Int
    var bio: String
    var profileImageName: String
    var interviewResponses: [InterviewResponse]
    var isInterviewComplete: Bool

    init(
        id: UUID = UUID(),
        name: String,
        age: Int,
        bio: String = "",
        profileImageName: String = "person.circle.fill",
        interviewResponses: [InterviewResponse] = [],
        isInterviewComplete: Bool = false
    ) {
        self.id = id
        self.name = name
        self.age = age
        self.bio = bio
        self.profileImageName = profileImageName
        self.interviewResponses = interviewResponses
        self.isInterviewComplete = isInterviewComplete
    }
}

struct InterviewResponse: Codable, Identifiable {
    let id: UUID
    let questionId: UUID
    let answer: String
    let selectedOptionIndex: Int?

    init(id: UUID = UUID(), questionId: UUID, answer: String, selectedOptionIndex: Int? = nil) {
        self.id = id
        self.questionId = questionId
        self.answer = answer
        self.selectedOptionIndex = selectedOptionIndex
    }
}
