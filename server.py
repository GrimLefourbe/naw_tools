import time
import sys

import flask
from flask_bootstrap import Bootstrap

from naw_tools import chasse, guerre2, formula
import os

application = flask.Flask(__name__)
bootstrap = Bootstrap(application)
application.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "test")

from flask_wtf import FlaskForm
from wtforms import (
    SubmitField,
    IntegerField,
    FloatField,
    TimeField,
    FormField,
    TextAreaField,
)
from wtforms.validators import InputRequired


class ChasseForm(FlaskForm):
    initial = IntegerField("TDC initial", validators=[InputRequired("TDC initial manquant")])
    chasse = IntegerField("TDC chassé", validators=[InputRequired("TDC chassé manquant")])
    submit = SubmitField("Calcule!")


class OptiChasseForm(FlaskForm):
    tdc_depart = IntegerField("TDC initial", validators=[InputRequired()])
    fdf = IntegerField("Force de frappe", validators=[InputRequired()])
    securite = FloatField(
        "Marge de sécurité (difficulté = fdf * securité)",
        default=1.15,
        validators=[InputRequired()],
    )
    n = IntegerField("Nombre de chasses", default=2, validators=[InputRequired()])
    submit = SubmitField("Optimise!")


class PositionField(FlaskForm):
    class Meta:
        csrf = False

    x = IntegerField("X", validators=[InputRequired()])
    y = IntegerField("Y", validators=[InputRequired()])


class DepartToArrivalForm(FlaskForm):
    depart = TimeField("Heure de départ", validators=[InputRequired()], format="%H:%M:%S")
    va = IntegerField("Vitesse d'attaque", validators=[InputRequired()], default=0)
    attaquant = FormField(PositionField)
    cible = FormField(PositionField)
    submit = SubmitField("Calcule!")


class RCAnalysisForm(FlaskForm):
    text = TextAreaField("RC")
    submit = SubmitField("Analyse")


@application.route("/")
def hello():
    return "Hello, world!"


@application.route("/chasse", methods=["GET", "POST"])
def chasse_calculator():
    chasse_form = ChasseForm()
    opti_chasse_form = OptiChasseForm()
    if chasse_form.validate_on_submit():

        diff = formula.difficulte_chasse2(initial=chasse_form.initial.data, chasse=chasse_form.chasse.data)

        res = f"{diff:,}".replace(",", " ")
        chasse_form.result = res

    elif opti_chasse_form.validate_on_submit():
        total, opti_chasses = chasse.opti_chasse(
            tdc_initial=opti_chasse_form.tdc_depart.data,
            diff=opti_chasse_form.fdf.data * opti_chasse_form.securite.data,
            n=opti_chasse_form.n.data,
        )
        opti_chasse_form.result = {
            "data": [(qte, dif, round(dif / opti_chasse_form.securite.data)) for qte, dif in opti_chasses]
        }
        opti_chasse_form.result["total"] = [sum(j) for j in zip(*opti_chasse_form.result["data"])]

    return flask.render_template(
        "chasse.html",
        time=time.time(),
        chasse_form=chasse_form,
        opti_chasse_form=opti_chasse_form,
    )


@application.route("/guerre", methods=["GET", "POST"])
def calculs():
    dureeform = DepartToArrivalForm()
    if dureeform.validate_on_submit():
        f = dureeform
        print(f.depart.data, file=sys.stderr)
        duree = guerre2.depart_to_arrival(
            depart=f.depart.data,
            x1=f.attaquant.x.data,
            y1=f.attaquant.y.data,
            x2=f.cible.x.data,
            y2=f.cible.y.data,
            va=f.va.data,
        )
        f.result = duree.strftime("%H:%M:%S")
    return flask.render_template("guerre.html", duree_form=dureeform)


@application.route("/rc", methods=["GET", "POST"])
def rc_analysis():
    rcform = RCAnalysisForm()
    if rcform.validate_on_submit():
        f = rcform
        results = guerre2.pipeline(f.text.data)
        armies_avant, armies_apres, niveaux = guerre2.format_stats(*results, mode="html")
        f.results = f"Niveaux\n{niveaux}\nAvant\n{armies_avant}\nAprès\n{armies_apres}"

    return flask.render_template("rc.html", rcform=rcform)


@application.route("/rc/csv", methods=["GET"])
def rc_csv():
    s = flask.request.args["text"]
    index = flask.request.args.get("index", False)
    columns = flask.request.args.get("columns", None)
    t = flask.request.args.get("type", "niveaux")
    if columns is not None:
        columns = columns.split(",")
    armies_avant, armies_apres, niveaux = guerre2.pipeline(s)
    armies_avant, armies_apres, niveaux = guerre2.format_stats(
        armies_avant, armies_apres, niveaux, index=index, columns=columns, mode="csv"
    )
    if t == "niveaux":
        return niveaux
    elif t == "avant":
        return armies_avant
    elif t == "apres":
        return armies_apres
    else:
        return flask.Response("Incorrect Type", status=415)


if __name__ == "__main__":
    print("running")
    application.run(host="0.0.0.0", debug=True)
