function createAccount() {
  console.log("HERE")
  var submitForm = document.getElementById("submitForm")
  var newUsername = document.getElementById("newUsername").value
  var newPassword = document.getElementById("newPassword").value
  submitForm.action = "/create/" + newUsername + "/" + newPassword
}
