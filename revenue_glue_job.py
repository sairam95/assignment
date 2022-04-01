import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.types import *
import pyspark.sql.functions as f
from pyspark.sql.window import Window
from urllib.parse import urlparse
from urllib.parse import parse_qs
import re
from datetime import date

# @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME', 's3_bucket', 's3_key'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)


class Constants:
    """
    Class to store all the constant variables.
    """
    Q_PARAM_DOMAINS = ["bing.com", "google.com"]
    P_PARAM_DOMAINS = ["yahoo.com"]


# function to extract domain from referrer
def extract_domains(url):
    """
    This is function to extract the domain from search url.
    Args:
        url(str): search url

    Returns(str):
        Returns google.com/yahoo.com/bing.com etc from search urls.
    """
    domain = urlparse(url).netloc
    return '.'.join(domain.split('.')[1:]).lower()


# converting above function to spark udf
udfextractDomains = f.udf(extract_domains, StringType())


# udf to extract the SearchKeyword
def extract_search_keyword(url, domain):
    """
    Function to parse the search keyword from referrer url based on domain.
    Args:
        url(str): search url
        domain(str): domain (yahoo, google etc) where the search is performed

    Returns(str):
        return the user search keyword

    """
    parsed_url = urlparse(url)
    if domain in Constants.P_PARAM_DOMAINS:
        parsed_keyword = parse_qs(parsed_url.query)['p'][0]
    elif domain in Constants.Q_PARAM_DOMAINS:
        parsed_keyword = parse_qs(parsed_url.query)['q'][0]
    else:
        parsed_keyword = None

    # cleaning the parsed keyword
    if parsed_keyword:
        _RE_COMBINE_WHITESPACE = re.compile(r"\s+")
        # removing multiple and lowercasing
        return _RE_COMBINE_WHITESPACE.sub(" ", parsed_keyword).strip().lower()
    else:
        return parsed_keyword


# converting above function to spark udf
udfextractSearchKeyword = f.udf(extract_search_keyword, StringType())


class SearchKeywordRevenue:
    """
    This class composes of functions to calculate the revenue that client getting
    from external Search Engines, such as Google, Yahoo and MSN, and which keywords are performing
    the best based on revenue?

    """
    FILE_SCHEMA = StructType([
        StructField("hit_time_gmt", StringType(), False),
        StructField("date_time", TimestampType(), False),
        StructField("user_agent", StringType(), False),
        StructField("ip", StringType(), False),
        StructField("event_list", StringType(), False),
        StructField("geo_city", StringType(), False),
        StructField("geo_region", StringType(), False),
        StructField("geo_country", StringType(), False),
        StructField("pagename", StringType(), False),
        StructField("page_url", StringType(), False),
        StructField("product_list", StringType(), False),
        StructField("referrer", StringType(), False)
    ]
    )

    def __init__(self, input_file_location, output_file_location):
        """
        Args:
            input_file_location(str): inbound s3 location of client hit level data
            output_file_location: output location of the final revenue file.
        """
        self.input_file_location = input_file_location
        self.output_file_location = output_file_location

    def read_file_to_df(self):
        """
        Reads a tab delimited csv file and returns the dataframe.
        Returns(dataframe):
        """
        df = spark.read.format("csv") \
            .option("header", "true") \
            .option("delimiter", "\t") \
            .schema(SearchKeywordRevenue.FILE_SCHEMA) \
            .load(self.input_file_location)
        return df

    def transform_df(self, df):
        """
        At high level this function performs a series of transformation to extract search keyword, domain and revenue
        for given hit level data.

         In detailed series of events:
            1) explodes the single product_list column which os ";" seperated to multiiple columns to extract revenue.
            2) extracts the domain and search keyword respectively from the referrer url.
            3) creates a new column event_type which marks a record as one of following categories
              "search", "order complete", "other" and filters the data for "search"
            4) ranks the data for each ip address based on order of events.
        Args:
            df: returns the spark dataframe with search and order complete event rows.

        Returns:

        """
        # exploding the product_list column into multiple columns to capture the revenue
        split_cols = f.split(df['product_list'], ';')
        transformed_df = df.withColumn('category', split_cols.getItem(0)) \
            .withColumn('product_name', split_cols.getItem(1)) \
            .withColumn('no_of_items', split_cols.getItem(2)) \
            .withColumn('total_revenue', split_cols.getItem(3)) \
            .withColumn('custom_event', split_cols.getItem(4)) \
            .withColumn('merchandizing_evar', split_cols.getItem(5))

        # extracting the domain and search keyword from referrer url as seperate columns
        domain_search_keyword_df = transformed_df.withColumn("domain", udfextractDomains("referrer")) \
            .withColumn("searchKeyword", udfextractSearchKeyword("referrer", "domain"))

        # filtering the dataframe with records for just search event and order completion event
        domain_search_keyword_df = domain_search_keyword_df.withColumn("event_type", f.when(
            ~f.col("domain").isNull() & ~f.col("searchKeyword").isNull(), "search")
                                                                       .when(f.col("event_list") == 1, "order complete")
                                                                       .otherwise("other"))
        # filtering the dataframe with records for just search event and order completion event
        search_order_comp_df = domain_search_keyword_df.filter(
            (f.col("event_type") == "search") | (f.col("event_type") == "order complete"))

        # ranking the search and order complete events for each ip address by hite time. Later this rank will be used
        # to calculate the revenue
        window_spec = Window.partitionBy("ip").orderBy("hit_time_gmt")
        ranked_df = search_order_comp_df.withColumn('total_revenue', f.col('total_revenue').cast("int")) \
            .withColumn("rank", f.rank().over(window_spec))
        return ranked_df

    def calculate_revenue(self, df):
        """
        calculates the revenue for each domain and each search keyword.
        Args:
            df:

        Returns:

        """
        df.createOrReplaceTempView("hit_level_data")
        # Filtering the search event rows
        spark.sql("select ip, domain, searchKeyword, total_revenue, rank "
                  "from hit_level_data where event_type ='search'").createOrReplaceTempView("search_event_df")
        # Filtering the order complete event rows
        spark.sql("select ip, domain, searchKeyword, total_revenue, rank  from hit_level_data where event_type='order "
                  "complete'").createOrReplaceTempView("order_complete_df")
        revenue_df = spark.sql("""select sed.domain as search_engine_domain, sed.searchKeyword as search_keyword, 
        sum(coalesce(ocd.total_revenue, 0)) as revenue from search_event_df sed left join order_complete_df ocd on 
        sed.ip = ocd.ip and sed.rank +1 = ocd.rank group by sed.domain, sed.searchKeyword order by revenue desc""")
        return revenue_df

    def write_df_to_s3(self, df):
        """
        Converts the spark dataframe to pandas dataframe and writes it as tab delimited file in s3.
        Args:
            df: spark dataframe

        Returns: None

        """
        pandas_df = df.toPandas()
        pandas_df.to_csv(self.output_file_location, sep='\t', encoding='utf-8')

    def process_file(self):
        """
        This function is point of execution to calculate the revenue for a search keyword.

        Returns: None
        """
        df = self.read_file_to_df()
        transformed_df = self.transform_df(df)
        revenue_df = self.calculate_revenue(transformed_df)
        self.write_df_to_s3(revenue_df)

input_file_location = "s3a://{0}/{1}".format(args['s3_bucket'], args['s3_key'])
output_file_location = "s3a://adobe-outbound/{0}/{0}_SearchKeywordPerformance.tab".format(str(date.today()))
skr = SearchKeywordRevenue(input_file_location=input_file_location, output_file_location=output_file_location)
skr.process_file()

job.commit()
