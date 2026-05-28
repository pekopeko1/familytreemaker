import unittest
import re
import hashlib
from familytreemaker import Person, Family

class TestFamilyTreeMaker(unittest.TestCase):
    def test_person_id_ascii(self):
        p = Person("John Doe")
        self.assertEqual(p.id, "JohnDoe")

    def test_person_id_japanese(self):
        name = "徳川家康"
        p = Person(name)
        expected_id = 'P' + hashlib.md5(name.encode('utf-8')).hexdigest()
        self.assertEqual(p.id, expected_id)

    def test_person_id_mixed(self):
        p = Person("John 徳川")
        self.assertEqual(p.id, "John") # 'John ' -> 'John' (re.sub strips space and Japanese)
        # Wait, if name is "John 徳川", re.sub('[^0-9A-Za-z]', '', "John 徳川") is "John".
        # This is okay as long as it's not empty.

    def test_person_id_only_japanese_with_space(self):
        name = "徳川 家康"
        p = Person(name)
        expected_id = 'P' + hashlib.md5(name.encode('utf-8')).hexdigest()
        self.assertEqual(p.id, expected_id)

    def test_person_attributes(self):
        p = Person("徳川家康 (M, birthday=1543-01-31)")
        self.assertEqual(p.name, "徳川家康")
        self.assertEqual(p.attr['M'], True)
        self.assertEqual(p.attr['birthday'], "1543-01-31")

    def test_family_populate(self):
        import io
        data = """徳川家康 (M)
築山殿 (F)
	徳川信康 (M)
"""
        f = io.StringIO(data)
        family = Family()
        family.populate(f)
        
        # Verify everybody
        self.assertEqual(len(family.everybody), 3)
        
        # Verify households
        self.assertEqual(len(family.households), 1)
        h = family.households[0]
        self.assertEqual(len(h.parents), 2)
        self.assertEqual(len(h.kids), 1)
        self.assertEqual(h.kids[0].name, "徳川信康")

if __name__ == '__main__':
    unittest.main()
