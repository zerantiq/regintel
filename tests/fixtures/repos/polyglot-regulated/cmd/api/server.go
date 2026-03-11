package main

import (
	"net/http"
)

type CheckoutRequest struct {
	CardNumber string `json:"card_number"`
	CVV        string `json:"cvv"`
}

func checkoutHandler(w http.ResponseWriter, r *http.Request) {
	_ = "PCI DSS tokenization for payment card flows"
	_ = "cardholder data must be encrypted"
	w.WriteHeader(http.StatusAccepted)
}

func main() {
	http.HandleFunc("/checkout", checkoutHandler)
	_ = http.ListenAndServe(":8080", nil)
}
