document.addEventListener("DOMContentLoaded", () => {
    const addExpenseButton = document.getElementById("addExpenseButton")
    const expenseModal = document.getElementById("expenseModal")
    const closeModal = document.getElementById("closeModal")

    const loginOverlay = document.getElementById("loginOverlay")
    const loginForm = document.getElementById("loginForm")
    const loginMessage = document.getElementById("loginMessage")
    const logoutButton = document.getElementById("logoutButton")
    const expenseSearch = document.getElementById("expenseSearch")

    expenseSearch.addEventListener("input", () => {
    loadExpenses(expenseSearch.value.trim())
})

logoutButton.addEventListener("click", () => {
    localStorage.removeItem("splitsmartToken")
    loginOverlay.classList.remove("hidden")
})

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault()

    const username = document.getElementById("loginUsername").value
    const password = document.getElementById("loginPassword").value

    const response = await fetch("/api/token/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })

    if (!response.ok) {
        loginMessage.textContent = "Invalid username or password."
        return
    }

    const data = await response.json()

    localStorage.setItem("splitsmartToken", data.token)
    loginOverlay.classList.add("hidden")
})

async function loadGroups() {
    const token = localStorage.getItem("splitsmartToken")

    const response = await fetch("/api/groups/", {
        headers: {
            "Authorization": `Token ${token}`
        }
    })

    if (!response.ok) {
        loginOverlay.classList.remove("hidden")
        return
    }

    const groups = await response.json()

    document.getElementById("groupCount").textContent = groups.length

    const groupList = document.getElementById("groupList")

groupList.innerHTML = groups.map(group => `
    <div class="group-item" onclick="loadDebts(${group.id})">
        <div>
            <strong>${group.name}</strong>
            <span>${group.members.length} members</span>
        </div>
        <span>›</span>
    </div>
`).join("")
}

loadGroups()

async function populateExpenseForm() {
    const token = localStorage.getItem("splitsmartToken")

    const [groupsResponse, usersResponse] = await Promise.all([
        fetch("/api/groups/", {
            headers: { "Authorization": `Token ${token}` }
        }),
        fetch("/api/users/", {
            headers: { "Authorization": `Token ${token}` }
        })
    ])

    const groups = await groupsResponse.json()
    const users = await usersResponse.json()

    document.getElementById("groupSelect").innerHTML = groups.map(group =>
        `<option value="${group.id}">${group.name}</option>`
    ).join("")

    document.getElementById("payerSelect").innerHTML = users.map(user =>
        `<option value="${user.id}">${user.username}</option>`
    ).join("")

    document.getElementById("participantSelect").innerHTML = users.map(user =>
        `<option value="${user.id}">${user.username}</option>`
    ).join("")
}

populateExpenseForm()

const expenseForm = document.getElementById("expenseForm")
const formMessage = document.getElementById("formMessage")

expenseForm.addEventListener("submit", async (event) => {
    event.preventDefault()

    const token = localStorage.getItem("splitsmartToken")

    const participants = Array.from(
        document.getElementById("participantSelect").selectedOptions
    ).map(option => Number(option.value))

    const response = await fetch("/api/expenses/", {
        method: "POST",
        headers: {
            "Authorization": `Token ${token}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            description: document.getElementById("description").value,
            amount: document.getElementById("amount").value,
            group: Number(document.getElementById("groupSelect").value),
            paid_by: Number(document.getElementById("payerSelect").value),
            participants: participants
        })
    })

    if (!response.ok) {
        const error = await response.json()
        console.log(error)
        formMessage.textContent = "Could not save expense."
        return
    }

    expenseForm.reset()
    expenseModal.classList.add("hidden")

    await loadExpenses()
    await loadBalances()
})

async function loadBalances() {
    const token = localStorage.getItem("splitsmartToken")

    const meResponse = await fetch("/api/me/", {
        headers: {
            "Authorization": `Token ${token}`
        }
    })

    const me = await meResponse.json()

    const groupsResponse = await fetch("/api/groups/", {
        headers: {
            "Authorization": `Token ${token}`
        }
    })

    const groups = await groupsResponse.json()

    let totalBalance = 0

    for (const group of groups) {
        const balanceResponse = await fetch(`/api/groups/${group.id}/balances/`, {
            headers: {
                "Authorization": `Token ${token}`
            }
        })

        const balances = await balanceResponse.json()

        const myBalance = balances.find(
            balance => balance.user_id === me.id
        )

        if (myBalance) {
            totalBalance += Number(myBalance.balance)
        }
    }

    document.getElementById("totalOwed").textContent =
        `$${Math.max(totalBalance, 0).toFixed(2)}`

    document.getElementById("totalOwe").textContent =
        `$${Math.max(-totalBalance, 0).toFixed(2)}`
}

loadBalances()

window.loadDebts = async function(groupId) {
    const token = localStorage.getItem("splitsmartToken")

    const response = await fetch(`/api/groups/${groupId}/debts/`, {
        headers: {
            "Authorization": `Token ${token}`
        }
    })

    const debts = await response.json()

    const debtList = document.getElementById("debtList")

debtList.innerHTML = debts.map(debt => `
    <div class="debt-item">
        <strong>${debt.from}</strong>
        <span>pays</span>
        <strong>${debt.to}</strong>
        <strong>$${Number(debt.amount).toFixed(2)}</strong>
    </div>
`).join("")
}

async function loadExpenses(search = "") {
    const token = localStorage.getItem("splitsmartToken")

    const response = await fetch(
        `/api/expenses/?search=${encodeURIComponent(search)}`,
        {
            headers: {
                "Authorization": `Token ${token}`
            }
        }
    )

    const expenses = await response.json()

    if (search === "") {
        const totalExpenses = expenses.reduce((total, expense) => {
            return total + Number(expense.amount)
        }, 0)

        document.getElementById("totalExpenses").textContent =
            `$${totalExpenses.toFixed(2)}`
    }

    const expenseList = document.getElementById("expenseList")

    if (expenses.length === 0) {
    expenseList.innerHTML = `
        <div class="empty-state">
            No expenses found.
        </div>
    `
} else {
    expenseList.innerHTML = expenses.map(expense => `
        <div class="expense-item">
            <div>
                <strong>${expense.description}</strong>
                <span>Shared expense</span>
            </div>
            <strong>$${Number(expense.amount).toFixed(2)}</strong>
        </div>
    `).join("")
}}

loadExpenses()

    addExpenseButton.addEventListener("click", () => {
        expenseModal.classList.remove("hidden")
    })

    closeModal.addEventListener("click", () => {
        expenseModal.classList.add("hidden")
    })

    expenseModal.addEventListener("click", (event) => {
        if (event.target === expenseModal) {
            expenseModal.classList.add("hidden")
        }
    })

    })