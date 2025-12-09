// go_services/performance/main.go
package main

// go_services/performance/main.go
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

type PerformanceRequest struct {
    StudentID int    `json:"student_id"`
    Semester  *int   `json:"semester,omitempty"`
    AuthToken string `json:"auth_token"`
}

type PerformanceResponse struct {
    Success    bool                        `json:"success"`
    AvgGrade   float64                     `json:"avg_grade,omitempty"`
    Semesters  map[int]map[string]SubjectData `json:"semesters,omitempty"`
    Error      string                      `json:"error,omitempty"`
}

type SubjectData struct {
    Teacher string  `json:"teacher"`
    Avg     float64 `json:"avg"`
    Grades  []GradeData `json:"grades"`
}

type GradeData struct {
    Date  string `json:"date"`
    Value int    `json:"value"`
    Type  string `json:"type"`
}

type Grade struct {
    ID             uint      `gorm:"primaryKey;column:id"`
    StudentID      uint      `gorm:"column:student_id"`
    GroupSubjectID uint      `gorm:"column:group_subject_id"`
    GroupSubject   GroupSubject `gorm:"foreignKey:GroupSubjectID"`
    GradeValue     int       `gorm:"column:grade"`
    GradeType      string    `gorm:"column:grade_type"`
    DateField      time.Time `gorm:"column:date"`
}

func (Grade) TableName() string {
    return "accounts_grade"
}

type GroupSubject struct {
    ID       uint    `gorm:"primaryKey;column:id"`
    GroupID  uint    `gorm:"column:group_id"`
    SubjectID uint   `gorm:"column:subject_id"`
    Semester int     `gorm:"column:semester"`
    Teacher  string  `gorm:"column:teacher"`
    Subject  Subject `gorm:"foreignKey:SubjectID"`
}

func (GroupSubject) TableName() string {
    return "accounts_groupsubject"
}

type Subject struct {
    ID          uint   `gorm:"primaryKey;column:id"`
    Name        string `gorm:"column:name"`
    Description string `gorm:"column:description"`
}

func (Subject) TableName() string {
    return "accounts_subject"
}

type DatabaseConfig struct {
    Host     string
    Port     string
    User     string
    Password string
    DBName   string
}

func getDBConfig() DatabaseConfig {
    
    return DatabaseConfig{
        Host:     mustGetEnv("DB_HOST"),
        Port:     mustGetEnv("DB_PORT"),
        User:     mustGetEnv("DB_USER"),
        Password: mustGetSecret("DB_PASSWORD"),
        DBName:   mustGetEnv("DB_NAME"),
    }
}

func mustGetEnv(key string) string {
    value := os.Getenv(key)
    if value == "" {
        log.Fatalf("Environment variable %s is required", key)
    }
	return value
}

func initDB() (*gorm.DB, error) {
    config := getDBConfig()
    
    dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
        config.Host, config.Port, config.User, config.Password, config.DBName)
    
    db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
    if err != nil {
        return nil, err
    }
    
    return db, nil
}

func calculatePerformance(studentID int, semester *int) (PerformanceResponse, error) {
    db, err := initDB()
    if err != nil {
        return PerformanceResponse{Success: false, Error: "Database connection failed"}, err
    }

    var grades []Grade
    
    query := db.
        Preload("GroupSubject").
        Preload("GroupSubject.Subject").
        Where("student_id = ?", studentID)
    
    if semester != nil {
        query = query.
            Where("gs.semester = ?", *semester)
    }
    
    err = query.Find(&grades).Error
    if err != nil {
        return PerformanceResponse{Success: false, Error: "Failed to fetch grades"}, err
    }
    
    if len(grades) == 0 {
        return PerformanceResponse{
            Success: true,
			
            AvgGrade: 0,
            Semesters: make(map[int]map[string]SubjectData),
        }, nil
    }
    
    semestersData := make(map[int]map[string]SubjectData)
    var totalSum float64
    var totalCount int
    
    for _, grade := range grades {
        semesterNum := grade.GroupSubject.Semester
        subjectName := grade.GroupSubject.Subject.Name
        teacher := grade.GroupSubject.Teacher
        
        if _, exists := semestersData[semesterNum]; !exists {
            semestersData[semesterNum] = make(map[string]SubjectData)
        }
        
        subjectData, exists := semestersData[semesterNum][subjectName]
        if !exists {
            subjectData = SubjectData{
                Teacher: teacher,
                Grades:  []GradeData{},
            }
        }
        
        
        semestersData[semesterNum][subjectName] = subjectData
        
        totalSum += float64(grade.GradeValue)
        totalCount++
    }
    
    for semesterNum, subjects := range semestersData {
        for subjectName, subjectData := range subjects {
            var sum float64
            var count int
            
            for _, grade := range subjectData.Grades {
                sum += float64(grade.Value)
                count++
            }
            
            if count > 0 {
                subjectData.Avg = round(sum/float64(count), 2)
                semestersData[semesterNum][subjectName] = subjectData
            }
        }
    }
    
    var avgGrade float64
    if totalCount > 0 {
        avgGrade = round(totalSum/float64(totalCount), 2)
    }
    
    return PerformanceResponse{
        Success:   true,
        AvgGrade:  avgGrade,
        Semesters: semestersData,
    }, nil
}

func sanitizeGradeType(gradeType string) string {
    allowedTypes := map[string]bool{
        "exam": true,
    }
    
    if allowedTypes[gradeType] {
        return gradeType
    }
    return "unknown"
}

func validateStudentID(studentID int) bool {
    return studentID > 0
}

func validateSemester(semester *int) bool {
    if semester == nil {
        return true
    }
    return *semester >= 1 && *semester <= 12
}

func round(value float64, precision int) float64 {
    ratio := 1.0
    for i := 0; i < precision; i++ {
        ratio *= 10.0
    }
    return float64(int(value*ratio+0.5)) / ratio
}

func performanceHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")

    if r.Method != http.MethodPost {
        w.WriteHeader(http.StatusMethodNotAllowed)
        json.NewEncoder(w).Encode(PerformanceResponse{
            Success: false,
            Error:   "Method not allowed",
        })
        return
    }

    var req PerformanceRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(PerformanceResponse{
            Success: false,
            Error:   "Invalid JSON format",
        })
        return
    }

    if req.AuthToken != os.Getenv("API_SECRET") {
        w.WriteHeader(http.StatusUnauthorized)
        json.NewEncoder(w).Encode(PerformanceResponse{
            Success: false,
            Error:   "Unauthorized",
        })
        return
    }

    if !validateStudentID(req.StudentID) {
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(PerformanceResponse{
            Success: false,
            Error:   "Invalid student ID",
        })
        return
    }

    if !validateSemester(req.Semester) {
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(PerformanceResponse{
            Success: false,
            Error:   "Invalid semester value",
        })
        return
    }

    result, err := calculatePerformance(req.StudentID, req.Semester)
    if err != nil {
        log.Printf("Error calculating performance: %v", err)
        w.WriteHeader(http.StatusInternalServerError)
        json.NewEncoder(w).Encode(PerformanceResponse{
            Success: false,
            Error:   "Internal server error",
        })
        return
    }

    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(result)
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    
    db, err := initDB()
    if err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        json.NewEncoder(w).Encode(map[string]string{
            "status":  "unhealthy",
            "message": "Database connection failed",
        })
        return
    }
    
    var count int64
    err = db.Model(&Grade{}).Count(&count).Error
    if err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        json.NewEncoder(w).Encode(map[string]string{
            "status":  "unhealthy",
            "message": "Database tables not accessible",
        })
        return
    }

    json.NewEncoder(w).Encode(map[string]string{
        "status":  "healthy",
        "service": "performance-calculator-gorm",
    })
}

func main() {
    godotenv.Load()

    r := mux.NewRouter()
    r.HandleFunc("/api/performance", performanceHandler).Methods("POST")
    r.HandleFunc("/health", healthCheck).Methods("GET")

    port := os.Getenv("PORT")
    if port == "" {
        port = "8081"
    }

    log.Printf("Performance Calculation Service started on :%s", port)
    log.Fatal(http.ListenAndServe(":"+port, r))
}