package main

import "os"

func persistCustomer(db DB, email string, payload []byte) string {
	db.Exec("INSERT INTO users(email) VALUES(?)", email)
	os.WriteFile("customer-export.txt", payload, 0o644)
	return email
}
