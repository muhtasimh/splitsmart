document.addEventListener("DOMContentLoaded", () => {
    const token = () => localStorage.getItem("splitsmartToken")
    const authHeaders = () => ({ "Authorization": `Token ${token()}` })
    const loginOverlay = document.getElementById("loginOverlay")
    const expenseModal = document.getElementById("expenseModal")
    const groupModal = document.getElementById("groupModal")

    function showView(name) {
        document.querySelectorAll(".app-view").forEach(view => view.classList.remove("active"))
        document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.view === name))
        document.getElementById(`${name}View`).classList.add("active")
        window.location.hash = name === "dashboard" ? "" : name
    }

    document.querySelectorAll(".nav-item").forEach(item => item.addEventListener("click", () => showView(item.dataset.view)))
    const initialView = ["expenses", "groups", "settlements"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard"
    showView(initialView)

    document.getElementById("logoutButton").addEventListener("click", () => {
        localStorage.removeItem("splitsmartToken")
        loginOverlay.classList.remove("hidden")
    })

    document.getElementById("loginForm").addEventListener("submit", async event => {
        event.preventDefault()
        const response = await fetch("/api/token/", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: loginUsername.value, password: loginPassword.value })
        })
        if (!response.ok) { loginMessage.textContent = "Invalid username or password."; return }
        const data = await response.json()
        localStorage.setItem("splitsmartToken", data.token)
        loginOverlay.classList.add("hidden")
        loginMessage.textContent = ""
        await refreshAll()
    })

    async function getUsers() {
        const response = await fetch("/api/users/", { headers: authHeaders() })
        return response.ok ? response.json() : []
    }

    async function loadGroups() {
        const response = await fetch("/api/groups/", { headers: authHeaders() })
        if (!response.ok) { loginOverlay.classList.remove("hidden"); return [] }
        const groups = await response.json()
        groupCount.textContent = groups.length
        const markup = groups.length ? groups.map(group => `
            <button class="group-item" data-group-id="${group.id}">
                <div><strong>${group.name}</strong><span>${group.members.length} member${group.members.length === 1 ? "" : "s"}</span></div><span>›</span>
            </button>`).join("") : '<div class="empty-state">No groups yet. Create your first group.</div>'
        dashboardGroupList.innerHTML = markup
        groupsPageList.innerHTML = markup
        settlementGroupList.innerHTML = markup
        document.querySelectorAll("[data-group-id]").forEach(el => el.addEventListener("click", async () => {
            showView("settlements")
            await loadDebts(el.dataset.groupId)
        }))
        return groups
    }

    async function populateForms(groups) {
        const users = await getUsers()
        groupSelect.innerHTML = groups.map(g => `<option value="${g.id}">${g.name}</option>`).join("")
        payerSelect.innerHTML = users.map(u => `<option value="${u.id}">${u.username}</option>`).join("")
        participantSelect.innerHTML = users.map(u => `<option value="${u.id}">${u.username}</option>`).join("")
        groupMembers.innerHTML = users.map(u => `<option value="${u.id}">${u.username}</option>`).join("")
    }

    async function loadExpenses(search = "") {
        const response = await fetch(`/api/expenses/?search=${encodeURIComponent(search)}`, { headers: authHeaders() })
        if (!response.ok) return []
        const expenses = await response.json()
        if (!search) totalExpenses.textContent = `$${expenses.reduce((sum, e) => sum + Number(e.amount), 0).toFixed(2)}`
        const markup = expenses.length ? expenses.map(e => `<div class="expense-item"><div><strong>${e.description}</strong><span>Shared expense</span></div><strong>$${Number(e.amount).toFixed(2)}</strong></div>`).join("") : '<div class="empty-state">No expenses found.</div>'
        expenseList.innerHTML = markup
        if (!search) dashboardExpenseList.innerHTML = markup
        return expenses
    }

    async function loadBalances(groups) {
        const meResponse = await fetch("/api/me/", { headers: authHeaders() })
        if (!meResponse.ok) return
        const me = await meResponse.json()
        let total = 0
        for (const group of groups) {
            const response = await fetch(`/api/groups/${group.id}/balances/`, { headers: authHeaders() })
            if (!response.ok) continue
            const balances = await response.json()
            const mine = balances.find(b => b.user_id === me.id)
            if (mine) total += Number(mine.balance)
        }
        totalOwed.textContent = `$${Math.max(total, 0).toFixed(2)}`
        totalOwe.textContent = `$${Math.max(-total, 0).toFixed(2)}`
    }

    async function loadDebts(groupId) {
        const response = await fetch(`/api/groups/${groupId}/debts/`, { headers: authHeaders() })
        if (!response.ok) return
        const debts = await response.json()
        debtList.innerHTML = debts.length ? debts.map(d => `<div class="debt-item"><strong>${d.from}</strong><span>pays</span><strong>${d.to}</strong><strong>$${Number(d.amount).toFixed(2)}</strong></div>`).join("") : '<div class="empty-state">Everyone in this group is settled up.</div>'
    }

    async function refreshAll() {
        if (!token()) { loginOverlay.classList.remove("hidden"); return }
        const groups = await loadGroups()
        await Promise.all([loadExpenses(), populateForms(groups), loadBalances(groups)])
    }

    expenseSearch.addEventListener("input", () => loadExpenses(expenseSearch.value.trim()))
    document.querySelectorAll(".open-expense").forEach(button => button.addEventListener("click", () => expenseModal.classList.remove("hidden")))
    closeExpenseModal.addEventListener("click", () => expenseModal.classList.add("hidden"))
    openGroupModal.addEventListener("click", () => groupModal.classList.remove("hidden"))
    closeGroupModal.addEventListener("click", () => groupModal.classList.add("hidden"))
    ;[expenseModal, groupModal].forEach(modal => modal.addEventListener("click", event => { if (event.target === modal) modal.classList.add("hidden") }))

    expenseForm.addEventListener("submit", async event => {
        event.preventDefault()
        const participants = Array.from(participantSelect.selectedOptions).map(o => Number(o.value))
        const response = await fetch("/api/expenses/", {
            method: "POST", headers: { ...authHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify({ description: description.value, amount: amount.value, group: Number(groupSelect.value), paid_by: Number(payerSelect.value), participants })
        })
        if (!response.ok) { formMessage.textContent = "Could not save expense."; return }
        expenseForm.reset(); expenseModal.classList.add("hidden"); formMessage.textContent = ""; await refreshAll()
    })

    groupForm.addEventListener("submit", async event => {
        event.preventDefault()
        const members = Array.from(groupMembers.selectedOptions).map(o => Number(o.value))
        if (!members.length) { groupFormMessage.textContent = "Select at least one member."; return }
        const response = await fetch("/api/groups/", {
            method: "POST", headers: { ...authHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify({ name: groupName.value.trim(), members })
        })
        if (!response.ok) { groupFormMessage.textContent = "Could not create group."; return }
        groupForm.reset(); groupModal.classList.add("hidden"); groupFormMessage.textContent = ""; await refreshAll()
    })

    refreshAll()
})