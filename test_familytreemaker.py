import unittest
from io import StringIO
from familytreemaker import Person, Household, Family

class TestPerson(unittest.TestCase):
    def test_person_creation_simple(self):
        p = Person("John Doe")
        self.assertEqual(p.name, "John Doe")
        self.assertEqual(p.id, "JohnDoe")
        self.assertEqual(p.attr, {})

    def test_person_creation_with_attributes(self):
        p = Person("Jane Doe (gender=F,id=JDoe1,custom=value)")
        self.assertEqual(p.name, "Jane Doe")
        self.assertEqual(p.id, "JDoe1")
        self.assertIn("gender", p.attr)
        self.assertEqual(p.attr["gender"], "F")
        self.assertIn("custom", p.attr)
        self.assertEqual(p.attr["custom"], "value")
        self.assertNotIn("id", p.attr) # id should be moved to p.id

    def test_person_id_generation_simple(self):
        p = Person("Common Name")
        self.assertEqual(p.id, "CommonName")

    def test_person_id_generation_with_unique_attr(self):
        # Hard to test randomness, but ensure it generates an ID and doesn't crash
        p1 = Person("Unique Name (unique)")
        p2 = Person("Unique Name (unique)")
        self.assertRegex(p1.id, r"UniqueName\d{3}")
        self.assertRegex(p2.id, r"UniqueName\d{3}")
        self.assertNotEqual(p1.id, p2.id, "Unique IDs should differ due to random suffix")

    def test_person_id_from_attr(self):
        p = Person("Specific ID Person (id=Person123)")
        self.assertEqual(p.id, "Person123")


class TestHousehold(unittest.TestCase):
    def test_household_creation(self):
        h = Household()
        self.assertEqual(h.parents, [])
        self.assertEqual(h.kids, [])
        self.assertTrue(h.isempty())

    def test_household_isempty(self):
        h = Household()
        self.assertTrue(h.isempty())

        p1 = Person("Parent 1")
        h.parents.append(p1)
        self.assertFalse(h.isempty())
        h.parents.pop() # clear for next check
        self.assertTrue(h.isempty())

        k1 = Person("Kid 1")
        h.kids.append(k1)
        self.assertFalse(h.isempty())


class TestFamily(unittest.TestCase):
    def setUp(self):
        self.family = Family()

    def test_add_person_new(self):
        p = self.family.add_person("New Person")
        self.assertIn(p.id, self.family.everybody)
        self.assertEqual(self.family.everybody[p.id].name, "New Person")

    def test_add_person_existing_updates_attributes(self):
        p1 = self.family.add_person("Existing Person (gender=M)")
        self.assertEqual(self.family.everybody[p1.id].attr.get("gender"), "M")

        p2 = self.family.add_person("Existing Person (city=NewTown)")
        self.assertEqual(p1.id, p2.id) # Should be the same person
        self.assertEqual(self.family.everybody[p1.id].attr.get("gender"), "M")
        self.assertEqual(self.family.everybody[p1.id].attr.get("city"), "NewTown")

    def test_add_household_valid(self):
        p1 = self.family.add_person("Parent One")
        p2 = self.family.add_person("Parent Two")
        h = Household()
        h.parents.extend([p1, p2])

        self.family.add_household(h)
        self.assertIn(h, self.family.households)
        self.assertEqual(h.id, 0) # First household

    def test_add_household_updates_person_households_list(self):
        p1 = self.family.add_person("Parent A")
        p2 = self.family.add_person("Parent B")
        h = Household()
        h.parents.extend([p1, p2])

        self.family.add_household(h)
        self.assertIn(h, p1.households)
        self.assertIn(h, p2.households)

    def test_add_household_invalid_parents_too_few(self):
        p1 = self.family.add_person("Single Parent")
        h = Household()
        h.parents.append(p1)
        with self.assertRaisesRegex(ValueError, "Household must have exactly 2 parents, got 1"):
            self.family.add_household(h)

    def test_add_household_invalid_parents_too_many(self):
        p1 = self.family.add_person("Parent X")
        p2 = self.family.add_person("Parent Y")
        p3 = self.family.add_person("Parent Z")
        h = Household()
        h.parents.extend([p1, p2, p3])
        with self.assertRaisesRegex(ValueError, "Household must have exactly 2 parents, got 3"):
            self.family.add_household(h)

    def test_find_person_by_id(self):
        p1 = self.family.add_person("Person With ID (id=XYZ123)")
        found_p = self.family.find_person("XYZ123")
        self.assertEqual(p1, found_p)

    def test_find_person_by_name(self):
        p1 = self.family.add_person("Named Person")
        found_p = self.family.find_person("Named Person")
        self.assertEqual(p1, found_p)

    def test_find_person_by_name_multiple_with_same_name_returns_first_added_by_id_logic(self):
        # This test depends on current find_person logic: id check first, then name.
        # If IDs are different, it will find by name.
        # If names are identical, and IDs are generated, they'd be "SameName", "SameName2" etc.
        # If id is specified, it finds that.
        p_name_only = self.family.add_person("Same Name") # ID: SameName
        p_name_and_id = self.family.add_person("Same Name (id=UniqueSN)") # ID: UniqueSN

        # Should find the one whose name matches, if ID doesn't match query "Same Name"
        found_p = self.family.find_person("Same Name")
        self.assertEqual(found_p.id, "SameName")

    def test_find_person_not_found(self):
        self.assertIsNone(self.family.find_person("NonExistent Person"))

    def test_find_first_ancestor_simple(self):
        p_ancestor = self.family.add_person("Ancestor")
        p_child = self.family.add_person("Child")

        h = Household()
        h.parents.extend([p_ancestor, self.family.add_person("Spouse")])
        h.kids.append(p_child)
        p_child.parents = h.parents # Manually set child's parents for this test
        self.family.add_household(h)

        found_ancestor = self.family.find_first_ancestor()
        # The ancestor could be "Ancestor" or "Spouse" depending on internal dict order
        self.assertIn(found_ancestor.name, ["Ancestor", "Spouse"])
        self.assertEqual(len(found_ancestor.parents), 0)


    def test_find_first_ancestor_none_found_all_have_parents(self):
        p1 = self.family.add_person("Parent Alpha")
        p2 = self.family.add_person("Parent Beta")
        p_child = self.family.add_person("Child Gamma")

        h = Household()
        h.parents.extend([p1, p2])
        h.kids.append(p_child)
        self.family.add_household(h)
        # Crucially, set parents for p1 and p2 as well
        p_child.parents = h.parents
        p1.parents = [self.family.add_person("Grandparent 1"), self.family.add_person("Grandparent 2")] # Dummy parents
        p2.parents = [self.family.add_person("Grandparent 3"), self.family.add_person("Grandparent 4")] # Dummy parents

        with self.assertRaisesRegex(ValueError, "No ancestor found; all persons have parents."):
            self.family.find_first_ancestor()

    def test_find_first_ancestor_empty_family(self):
        with self.assertRaisesRegex(ValueError, "Cannot find an ancestor in an empty family."):
            self.family.find_first_ancestor()

    def test_populate_simple(self):
        file_content = """
GrandPa
GrandMa
	ParentA
	ParentB (gender=M)
		Child1 (id=C1)
		Child2

OtherPerson
"""
        fake_file = StringIO(file_content)
        self.family.populate(fake_file)

        self.assertIsNotNone(self.family.find_person("GrandPa"))
        self.assertIsNotNone(self.family.find_person("GrandMa"))
        parent_a = self.family.find_person("ParentA")
        self.assertIsNotNone(parent_a)
        parent_b = self.family.find_person("ParentB")
        self.assertIsNotNone(parent_b)
        self.assertEqual(parent_b.attr.get("gender"), "M")

        child1 = self.family.find_person("C1")
        self.assertIsNotNone(child1)
        self.assertEqual(child1.name, "Child1")

        self.assertIsNotNone(self.family.find_person("Child2"))
        self.assertIsNotNone(self.family.find_person("OtherPerson"))

        # Check household structure (basic)
        self.assertEqual(len(self.family.households), 2) # GP-GM household, PA-PB household

        # GrandPa and GrandMa should be parents of ParentA and ParentB
        # This requires checking the actual parent objects, which populate sets up.
        self.assertIn(self.family.find_person("GrandPa"), parent_a.parents)
        self.assertIn(self.family.find_person("GrandMa"), parent_a.parents)
        self.assertIn(self.family.find_person("GrandPa"), parent_b.parents)
        self.assertIn(self.family.find_person("GrandMa"), parent_b.parents)

        # ParentA and ParentB should be parents of Child1 and Child2
        self.assertIn(parent_a, child1.parents)
        self.assertIn(parent_b, child1.parents)
        self.assertIn(parent_a, self.family.find_person("Child2").parents)
        self.assertIn(parent_b, self.family.find_person("Child2").parents)

        # OtherPerson should have no parents in this structure
        self.assertEqual(len(self.family.find_person("OtherPerson").parents), 0)


if __name__ == '__main__':
    unittest.main()
