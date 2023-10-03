import unittest
from localhost_proxy import CacheContainer
from datetime import datetime, timedelta
import threading
import time

class TestStringMethods(unittest.TestCase):

    def test_not_exists(self):
        cache = CacheContainer("store", 1)
        self.assertEqual(None, cache.get("notexists"))

    def test_max_queue_size_one(self):
        cache = CacheContainer("store", 1)
        value1 = {"expiration": datetime.now() + timedelta(minutes=1), "content": "one"}
        value2 = {"expiration": datetime.now() + timedelta(minutes=1), "content": "two"}
        cache.put("one", value1)
        self.assertEqual(value1, cache.get("one"))
        # Second item should not be on the cache
        self.assertEqual(None, cache.get("two"))
        # Since cache_queue is only one only the second item will have value on the cache and the first one cleared
        cache.put("two", value2)
        cache.clear_cache()
        self.assertEqual(value2, cache.get("two"))
        self.assertEqual(None, cache.get('one'))

    def test_expire_on_time(self):
        cache = CacheContainer("store", 1)
        self.assertEqual(cache.cache_keys.qsize(), 0)
        cache.clear_cache()
        self.assertEqual(cache.cache_keys.qsize(), 0)
        value1 = {"expiration": datetime.now() + timedelta(seconds=3), "content": "one"}
        cache.put("one", value1)
        self.assertEqual(value1, cache.get("one"))
        time.sleep(5)
        cache.clear_cache()
        self.assertEqual(None, cache.get("one"))

    def test_insert_twice(self):
        cache = CacheContainer("store", 1)
        value1 = {"expiration": datetime.now() + timedelta(seconds=3), "content": "one"}
        cache.put("one", value1)
        self.assertEqual(value1, cache.get("one"))
        # Insert element again with higher expiration
        value1 = {"expiration": datetime.now() + timedelta(seconds=4), "content": "one"}
        cache.put("one", value1)
        self.assertEqual(value1, cache.get("one"))
        time.sleep(5)
        cache.clear_cache()
        self.assertEqual(None, cache.get("one"))

    def test_multithreaded_cache_access(self):
        cache = CacheContainer("store", 1)
        num_threads = 10
        cache_value = {"expiration": datetime.now() + timedelta(minutes=2), "content": "test"}

        def insert_and_get():
            for i in range(100):
                cache.put("key" + str(i), cache_value)
                retrieved_value = cache.get("key" + str(i))
                # Queue size is one, assert each value is the value got or None
                if retrieved_value is not None:
                    self.assertEqual(retrieved_value, cache_value)

        # Create and start multiple threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=insert_and_get)
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        cache.clear_cache()
        for i in range(100):
            retrieved_value = cache.get("key" + str(i))
            if i < 99:
                self.assertEqual(retrieved_value, None)
            else:
                self.assertEqual(retrieved_value, cache_value)

if __name__ == '__main__':
    unittest.main()