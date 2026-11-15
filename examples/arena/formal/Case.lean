-- Synthetic arena case SHA-256: 08067e8c4ae2d9d1ff026dcec583a53dcc05dbf7dc36a968c82fdc3ed9ee3f17
namespace ArenaCase
def fact0 : Bool := true
def fact1 : Bool := false
def fact2 : Bool := true
abbrev admissible : Prop := ((fact1 = false) ∨ (fact0 = true))
abbrev claim : Prop := ((fact0 = true)) ∧ ((fact1 = true))
theorem consistent : admissible := by decide
theorem outcome : ¬ claim := by decide
#print axioms consistent
#print axioms outcome
end ArenaCase
